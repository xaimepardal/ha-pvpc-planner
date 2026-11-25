from datetime import datetime

import pytest

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.pvpc_planner.const import CONF_PRICE_ENTITY, DOMAIN
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

# Los tests con freeze_time empiezan a las 10:30 en Madrid: el token de acceso y
# los temporizadores se crean ya con esa hora.
TERMO = "input_boolean.termo"
LAVADORA = "input_boolean.lavadora"


async def _setup(hass: HomeAssistant, hass_ws_client):
    await hass.config.async_set_time_zone("Europe/Madrid")
    assert await async_setup_component(
        hass, "input_boolean", {"input_boolean": {"termo": {}, "lavadora": {}}}
    )
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_PRICE_ENTITY: "sensor.pvpc"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    # El websocket arranca el servidor HTTP: tiene que ir después de cargar frontend.
    return await hass_ws_client(hass)


async def _tick(hass, freezer, hour, minute=0):
    freezer.move_to(dt_util.as_utc(datetime(2026, 11, 25, hour, minute, tzinfo=dt_util.get_default_time_zone())))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


@pytest.mark.freeze_time("2026-11-25 09:30:00+00:00")
async def test_on_only_in_marked_hours(hass, hass_ws_client, freezer) -> None:
    ws = await _setup(hass, hass_ws_client)

    await ws.send_json_auto_id({"type": f"{DOMAIN}/subscribe"})
    assert (await ws.receive_json())["success"]
    assert (await ws.receive_json())["event"]["schedule"] == {}

    async def set_slot(hour, ids):
        await ws.send_json_auto_id(
            {"type": f"{DOMAIN}/set", "date": "2026-11-25", "hour": hour, "entity_ids": ids}
        )
        while (msg := await ws.receive_json())["type"] == "event":
            pass
        return msg

    # Hora pasada: rechazada.
    msg = await set_slot(9, [TERMO])
    assert not msg["success"]
    assert msg["error"]["code"] == "invalid_slot"

    # Hora en curso: se aplica al momento.
    assert (await set_slot(10, [TERMO]))["success"]
    await hass.async_block_till_done()
    assert hass.states.get(TERMO).state == "on"

    assert (await set_slot(11, [TERMO, LAVADORA]))["success"]
    assert hass.states.get(LAVADORA).state == "off"

    # Desde aquí no se usa el websocket: al avanzar el reloj caduca el token
    # (30 min) y HA cierra la conexión.
    await _tick(hass, freezer, 11)
    assert hass.states.get(TERMO).state == "on"
    assert hass.states.get(LAVADORA).state == "on"

    # Hora sin marcar: se apaga todo lo que encendió el planner.
    await _tick(hass, freezer, 12)
    assert hass.states.get(TERMO).state == "off"
    assert hass.states.get(LAVADORA).state == "off"

    # Lo encendido a mano fuera de la programación no se toca.
    await hass.services.async_call("input_boolean", "turn_on", {"entity_id": TERMO}, blocking=True)
    await _tick(hass, freezer, 13)
    assert hass.states.get(TERMO).state == "on"


@pytest.mark.freeze_time("2026-11-25 09:30:00+00:00")
async def test_unmark_current_hour_turns_off(hass, hass_ws_client, freezer) -> None:
    ws = await _setup(hass, hass_ws_client)
    for ids in ([TERMO], []):
        await ws.send_json_auto_id(
            {"type": f"{DOMAIN}/set", "date": "2026-11-25", "hour": 10, "entity_ids": ids}
        )
        assert (await ws.receive_json())["success"]
        await hass.async_block_till_done()
    assert hass.states.get(TERMO).state == "off"


async def test_config_flow(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "pvpc_missing"

    MockConfigEntry(domain="pvpc_hourly_pricing").add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PRICE_ENTITY: "sensor.pvpc"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
