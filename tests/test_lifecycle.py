"""Reinicio de HA y descarga/recarga de la entrada."""

from datetime import date

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState
import pytest

from custom_components.pvpc_planner.const import DOMAIN, PANEL_URL

from .common import (
    LAVADORA,
    NOW,
    TERMO,
    async_move_to,
    async_setup_integration,
    async_ws_set,
    is_on,
    local,
)

DAY = date(2026, 11, 25)


@pytest.mark.freeze_time(NOW)
async def test_restart_resumes_current_hour(hass, hass_storage) -> None:
    hass.set_state(CoreState.not_running)
    await async_setup_integration(
        hass,
        hass_storage,
        stored={
            "schedule": {
                "2026-11-24": {"10": [LAVADORA]},
                "2026-11-25": {"10": [TERMO], "11": [LAVADORA]},
            },
            # Encendida por el planner antes del reinicio y ya no marcada.
            "active": [LAVADORA],
        },
        initial_on=(LAVADORA,),
    )
    assert not is_on(hass, TERMO)
    assert is_on(hass, LAVADORA)

    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    assert is_on(hass, TERMO)
    assert not is_on(hass, LAVADORA)
    assert list(hass.data[DOMAIN].as_dict()["schedule"]) == ["2026-11-25"]


@pytest.mark.freeze_time(NOW)
async def test_unload_and_reload(hass, hass_ws_client, freezer) -> None:
    entry = await async_setup_integration(hass)
    ws = await hass_ws_client(hass)
    assert (await async_ws_set(ws, 10, [TERMO]))["success"]
    assert (await async_ws_set(ws, 12, [LAVADORA]))["success"]
    await hass.async_block_till_done()
    assert is_on(hass, TERMO)

    # Recargar no vuelve a registrar rutas ni comandos (fallaría) y no pierde
    # cambios pendientes del guardado diferido.
    assert await hass.config_entries.async_reload(entry.entry_id)
    assert hass.data[DOMAIN].slot(DAY, 12) == [LAVADORA]

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert DOMAIN not in hass.data
    assert PANEL_URL not in hass.data["frontend_panels"]
    await ws.send_json_auto_id({"type": f"{DOMAIN}/subscribe"})
    assert (await ws.receive_json())["error"]["code"] == "not_loaded"
    assert (await async_ws_set(ws, 12, []))["error"]["code"] == "not_loaded"

    # Descargado: el cambio de hora no apaga nada.
    await async_move_to(hass, freezer, local(2026, 11, 25, 11))
    assert is_on(hass, TERMO)

    # Al volver a cargar recupera la hora en curso: TERMO no está marcado a las 11.
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert PANEL_URL in hass.data["frontend_panels"]
    assert not is_on(hass, TERMO)
