"""Comandos websocket que usa el panel."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from homeassistant.auth.permissions.const import POLICY_CONTROL
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect
import voluptuous as vol

from .const import (
    ALLOWED_DOMAINS,
    DOMAIN,
    GROUP_PREFIX,
    MAX_ENTITIES_PER_SLOT,
    MAX_HIDDEN,
    SIGNAL_UPDATED,
)
from .planner import Planner

GROUP_ID = vol.Match(r"^[0-9a-f]{32}$")
ICON = vol.Match(r"^mdi:[a-z0-9]+(-[a-z0-9]+)*$")


def _allowed_entity_id(value: Any) -> str:
    entity_id = cv.entity_id(value)
    if cv.split_entity_id(entity_id)[0] not in ALLOWED_DOMAINS:
        raise vol.Invalid(f"Domain not allowed: {entity_id}")
    return entity_id


def _target(value: Any) -> str:
    """Entidad permitida o referencia a un grupo."""
    if isinstance(value, str) and value.startswith(GROUP_PREFIX):
        GROUP_ID(value.removeprefix(GROUP_PREFIX))
        return value
    return _allowed_entity_id(value)


def _entity_list(min_len: int, max_len: int) -> vol.All:
    return vol.All([_allowed_entity_id], vol.Length(min=min_len, max=max_len))


@callback
def async_register_commands(hass: HomeAssistant) -> None:
    for command in (ws_subscribe, ws_set, ws_group_save, ws_group_delete, ws_hidden):
        websocket_api.async_register_command(hass, command)


def _planner(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg_id: int
) -> Planner | None:
    if (planner := hass.data.get(DOMAIN)) is None:
        connection.send_error(msg_id, "not_loaded", "PVPC Planner is not loaded")
    return planner


def _check_control(
    connection: websocket_api.ActiveConnection, entity_ids: Iterable[str]
) -> None:
    user = connection.user
    for entity_id in entity_ids:
        if not user.permissions.check_entity(entity_id, POLICY_CONTROL):
            raise Unauthorized(user_id=user.id, entity_id=entity_id)


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/subscribe"})
@callback
def ws_subscribe(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    if (planner := _planner(hass, connection, msg["id"])) is None:
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
            [_target], vol.Length(max=MAX_ENTITIES_PER_SLOT)
        ),
    }
)
@websocket_api.async_response
async def ws_set(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    if (planner := _planner(hass, connection, msg["id"])) is None:
        return
    targets: list[str] = msg["entity_ids"]
    if missing := [
        t
        for t in targets
        if t.startswith(GROUP_PREFIX)
        and planner.group(t.removeprefix(GROUP_PREFIX)) is None
    ]:
        connection.send_error(msg["id"], "not_found", f"Unknown groups: {missing}")
        return
    # Añadir o quitar una entidad (o grupo) exige poder controlar sus entidades.
    changed = set(targets) ^ set(planner.slot(msg["date"], msg["hour"]))
    _check_control(connection, planner.entities(changed))
    try:
        await planner.async_set_slot(msg["date"], msg["hour"], targets)
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_slot", str(err))
        return
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/group/save",
        vol.Optional("group_id"): GROUP_ID,
        vol.Required("name"): vol.All(str, vol.Strip, vol.Length(min=1, max=40)),
        vol.Required("icon"): ICON,
        vol.Required("entity_ids"): _entity_list(1, MAX_ENTITIES_PER_SLOT),
    }
)
@websocket_api.async_response
async def ws_group_save(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    if (planner := _planner(hass, connection, msg["id"])) is None:
        return
    group_id = msg.get("group_id")
    old: list[str] = []
    if group_id is not None:
        if (group := planner.group(group_id)) is None:
            connection.send_error(msg["id"], "not_found", "Unknown group")
            return
        old = group["entity_ids"]
    # Cambiar un grupo cambia las horas que lo usan.
    _check_control(connection, {*old, *msg["entity_ids"]})
    try:
        group_id = await planner.async_save_group(
            group_id, msg["name"], msg["icon"], msg["entity_ids"]
        )
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_group", str(err))
        return
    connection.send_result(msg["id"], {"group_id": group_id})


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/group/delete", vol.Required("group_id"): GROUP_ID}
)
@websocket_api.async_response
async def ws_group_delete(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    if (planner := _planner(hass, connection, msg["id"])) is None:
        return
    if (group := planner.group(msg["group_id"])) is None:
        connection.send_error(msg["id"], "not_found", "Unknown group")
        return
    _check_control(connection, group["entity_ids"])
    await planner.async_delete_group(msg["group_id"])
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/hidden/set",
        vol.Required("entity_ids"): _entity_list(0, MAX_HIDDEN),
    }
)
@callback
def ws_hidden(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    if (planner := _planner(hass, connection, msg["id"])) is None:
        return
    _check_control(connection, set(msg["entity_ids"]) ^ set(planner.hidden))
    planner.set_hidden(msg["entity_ids"])
    connection.send_result(msg["id"])
