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
    MAX_CUSTOMIZED,
    MAX_ENTITIES_PER_SLOT,
    MAX_HIDDEN,
    MAX_RULES_PER_TEMPLATE,
    SIGNAL_UPDATED,
)
from .planner import Planner
from .rules import RULES

GROUP_ID = TEMPLATE_ID = vol.Match(r"^[0-9a-f]{32}$")
NAME = vol.All(str, vol.Strip, vol.Length(max=40))
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


def _rule(value: Any) -> dict[str, Any]:
    """{"rule": id, "params": {...}} validado con el esquema declarado por la regla."""
    item = vol.Schema(
        {vol.Required("rule"): vol.In(RULES), vol.Optional("params", default={}): dict}
    )(value)
    rule = item["rule"]
    return {"rule": rule, "params": RULES[rule].validate(item["params"])}


def _entity_list(min_len: int, max_len: int) -> vol.All:
    return vol.All([_allowed_entity_id], vol.Length(min=min_len, max=max_len))


@callback
def async_register_commands(hass: HomeAssistant) -> None:
    for command in (
        ws_subscribe,
        ws_set,
        ws_group_save,
        ws_group_delete,
        ws_hidden,
        ws_device,
        ws_template_save,
        ws_template_delete,
    ):
        websocket_api.async_register_command(hass, command)


def _planner(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg_id: int
) -> Planner | None:
    if (planner := hass.data.get(DOMAIN)) is None:
        connection.send_error(msg_id, "not_loaded", "PVPC Planner is not loaded")
    return planner


def _unknown_groups(planner: Planner, targets: Iterable[str]) -> list[str]:
    return [
        t
        for t in targets
        if t.startswith(GROUP_PREFIX)
        and planner.group(t.removeprefix(GROUP_PREFIX)) is None
    ]


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
    if missing := _unknown_groups(planner, targets):
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


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/device/set",
        vol.Required("entity_id"): _allowed_entity_id,
        # Vacío o ausente: vuelve al de Home Assistant.
        vol.Optional("name"): vol.Any(None, NAME),
        vol.Optional("icon"): vol.Any(None, "", ICON),
    }
)
@callback
def ws_device(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    if (planner := _planner(hass, connection, msg["id"])) is None:
        return
    entity_id = msg["entity_id"]
    _check_control(connection, [entity_id])
    if entity_id not in planner.devices and len(planner.devices) >= MAX_CUSTOMIZED:
        connection.send_error(msg["id"], "invalid_device", "Too many devices")
        return
    planner.set_device(entity_id, msg.get("name"), msg.get("icon"))
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/template/save",
        vol.Optional("template_id"): TEMPLATE_ID,
        vol.Required("rules"): vol.All(
            [_rule], vol.Length(min=1, max=MAX_RULES_PER_TEMPLATE)
        ),
        vol.Required("targets"): vol.All(
            [_target], vol.Length(min=1, max=MAX_ENTITIES_PER_SLOT)
        ),
    }
)
@websocket_api.async_response
async def ws_template_save(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    if (planner := _planner(hass, connection, msg["id"])) is None:
        return
    template_id = msg.get("template_id")
    old: list[str] = []
    if template_id is not None:
        if (template := planner.template(template_id)) is None:
            connection.send_error(msg["id"], "not_found", "Unknown template")
            return
        old = template["targets"]
    if missing := _unknown_groups(planner, msg["targets"]):
        connection.send_error(msg["id"], "not_found", f"Unknown groups: {missing}")
        return
    # Una plantilla enciende y apaga sus destinos: hace falta controlarlos todos.
    _check_control(connection, planner.entities({*old, *msg["targets"]}))
    try:
        template_id = await planner.async_save_template(
            template_id, msg["rules"], msg["targets"]
        )
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_template", str(err))
        return
    connection.send_result(msg["id"], {"template_id": template_id})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/template/delete",
        vol.Required("template_id"): TEMPLATE_ID,
    }
)
@websocket_api.async_response
async def ws_template_delete(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    if (planner := _planner(hass, connection, msg["id"])) is None:
        return
    if (template := planner.template(msg["template_id"])) is None:
        connection.send_error(msg["id"], "not_found", "Unknown template")
        return
    _check_control(connection, planner.entities(template["targets"]))
    await planner.async_delete_template(msg["template_id"])
    connection.send_result(msg["id"])
