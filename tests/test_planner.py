"""Encendidos y apagados según la programación (vía websocket)."""

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pvpc_planner.const import CONF_PRICE_ENTITY, DOMAIN

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


@pytest.mark.freeze_time(NOW)
async def test_on_only_in_marked_hours(hass, hass_ws_client, freezer) -> None:
    await async_setup_integration(hass)
    # El websocket arranca el servidor HTTP: tiene que ir después de cargar frontend.
    ws = await hass_ws_client(hass)

    await ws.send_json_auto_id({"type": f"{DOMAIN}/subscribe"})
    assert (await ws.receive_json())["success"]
    assert (await ws.receive_json())["event"]["schedule"] == {}

    msg = await async_ws_set(ws, 9, [TERMO])
    assert msg["error"]["code"] == "invalid_slot"

    # Hora en curso: se aplica al momento.
    assert (await async_ws_set(ws, 10, [TERMO]))["success"]
    await hass.async_block_till_done()
    assert is_on(hass, TERMO)

    assert (await async_ws_set(ws, 11, [TERMO, LAVADORA]))["success"]
    assert not is_on(hass, LAVADORA)

    await async_move_to(hass, freezer, local(2026, 11, 25, 11))
    assert is_on(hass, TERMO)
    assert is_on(hass, LAVADORA)

    # Hora sin marcar: se apaga todo lo que encendió el planner.
    await async_move_to(hass, freezer, local(2026, 11, 25, 12))
    assert not is_on(hass, TERMO)
    assert not is_on(hass, LAVADORA)

    # Lo encendido a mano fuera de la programación no se toca.
    await hass.services.async_call(
        "input_boolean", "turn_on", {"entity_id": TERMO}, blocking=True
    )
    await async_move_to(hass, freezer, local(2026, 11, 25, 13))
    assert is_on(hass, TERMO)


@pytest.mark.freeze_time(NOW)
async def test_unmark_current_hour_turns_off(hass, hass_ws_client) -> None:
    await async_setup_integration(hass)
    ws = await hass_ws_client(hass)
    for ids in ([TERMO], []):
        assert (await async_ws_set(ws, 10, ids))["success"]
        await hass.async_block_till_done()
    assert not is_on(hass, TERMO)


@pytest.mark.freeze_time(NOW)
async def test_manually_on_is_not_turned_off(hass, hass_ws_client, freezer) -> None:
    await async_setup_integration(hass, initial_on=(TERMO,))
    ws = await hass_ws_client(hass)
    assert (await async_ws_set(ws, 11, [TERMO]))["success"]

    await async_move_to(hass, freezer, local(2026, 11, 25, 11))
    await async_move_to(hass, freezer, local(2026, 11, 25, 12))
    assert is_on(hass, TERMO)


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
