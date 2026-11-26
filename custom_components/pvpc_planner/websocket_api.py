"""Comandos websocket que usa el panel."""

from __future__ import annotations

from typing import Any

from homeassistant.auth.permissions.const import POLICY_CONTROL
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect
import voluptuous as vol

from .const import DOMAIN, SIGNAL_UPDATED, SUPPORTED_DOMAINS


@callback
def async_register_commands(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_subscribe)
    websocket_api.async_register_command(hass, ws_set)


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/subscribe"})
@callback
def ws_subscribe(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    if (planner := hass.data.get(DOMAIN)) is None:
        connection.send_error(msg["id"], "not_loaded", "PVPC Planner no está cargado")
        return

    @callback
    def forward() -> None:
        connection.send_message(
            websocket_api.event_message(msg["id"], planner.as_dict())
        )

    connection.subscriptions[msg["id"]] = async_dispatcher_connect(
        hass, SIGNAL_UPDATED, forward
    )
    connection.send_result(msg["id"])
    forward()


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/set",
        vol.Required("date"): cv.date,
        vol.Required("hour"): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
        vol.Required("entity_ids"): [cv.entity_id],
    }
)
@websocket_api.async_response
async def ws_set(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    if (planner := hass.data.get(DOMAIN)) is None:
        connection.send_error(msg["id"], "not_loaded", "PVPC Planner no está cargado")
        return

    entity_ids: list[str] = msg["entity_ids"]
    if unsupported := [
        e for e in entity_ids if e.split(".")[0] not in SUPPORTED_DOMAINS
    ]:
        connection.send_error(
            msg["id"], "invalid_entity", f"Entidades no admitidas: {unsupported}"
        )
        return
    # Añadir o quitar una entidad de la hora exige poder controlarla.
    changed = set(entity_ids) ^ set(planner.slot(msg["date"], msg["hour"]))
    for entity_id in changed:
        if not connection.user.permissions.check_entity(entity_id, POLICY_CONTROL):
            raise Unauthorized(entity_id=entity_id, permission=POLICY_CONTROL)

    try:
        await planner.async_set_slot(msg["date"], msg["hour"], entity_ids)
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_slot", str(err))
        return
    connection.send_result(msg["id"])
