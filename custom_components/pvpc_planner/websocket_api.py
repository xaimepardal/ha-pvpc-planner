"""Comandos websocket que usa el panel."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.auth.permissions.const import POLICY_CONTROL
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import ALLOWED_DOMAINS, DOMAIN, MAX_ENTITIES_PER_SLOT, SIGNAL_UPDATED


def _allowed_entity_id(value: Any) -> str:
    entity_id = cv.entity_id(value)
    if cv.split_entity_id(entity_id)[0] not in ALLOWED_DOMAINS:
        raise vol.Invalid(f"Dominio no permitido: {entity_id}")
    return entity_id


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
        vol.Required("entity_ids"): vol.All(
            [_allowed_entity_id], vol.Length(max=MAX_ENTITIES_PER_SLOT)
        ),
    }
)
@websocket_api.async_response
async def ws_set(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    if (planner := hass.data.get(DOMAIN)) is None:
        connection.send_error(msg["id"], "not_loaded", "PVPC Planner no está cargado")
        return
    user = connection.user
    for entity_id in msg["entity_ids"]:
        if not user.permissions.check_entity(entity_id, POLICY_CONTROL):
            raise Unauthorized(user_id=user.id, entity_id=entity_id)
    try:
        await planner.async_set_slot(msg["date"], msg["hour"], msg["entity_ids"])
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_slot", str(err))
        return
    connection.send_result(msg["id"])
