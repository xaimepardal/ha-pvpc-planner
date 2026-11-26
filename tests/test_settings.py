"""Grupos y dispositivos ocultos."""

from datetime import date

from homeassistant.auth.models import Group
import pytest
from pytest_homeassistant_custom_component.common import MockUser

from custom_components.pvpc_planner.const import DOMAIN, MAX_CUSTOMIZED, MAX_GROUPS

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


async def _ws(ws, type_: str, **data) -> dict:
    await ws.send_json_auto_id({"type": f"{DOMAIN}/{type_}", **data})
    while (msg := await ws.receive_json())["type"] == "event":
        pass
    return msg


async def _save(ws, ids, **data) -> dict:
    return await _ws(
        ws, "group/save", name="Agua", icon="mdi:water-boiler", entity_ids=ids, **data
    )


async def _user_ws(hass, hass_ws_client, policy: dict):
    user = MockUser(groups=[Group(name="u", policy=policy)]).add_to_hass(hass)
    refresh = await hass.auth.async_create_refresh_token(user, "https://example.com/")
    return await hass_ws_client(hass, hass.auth.async_create_access_token(refresh))


@pytest.mark.freeze_time(NOW)
async def test_group_in_slot(hass, hass_ws_client, freezer) -> None:
    await async_setup_integration(hass)
    ws = await hass_ws_client(hass)
    group_id = (await _save(ws, [TERMO]))["result"]["group_id"]
    ref = f"group:{group_id}"

    assert (await async_ws_set(ws, 10, [ref]))["success"]
    await hass.async_block_till_done()
    assert is_on(hass, TERMO)

    # Editar el grupo de la hora en curso se aplica al momento.
    assert (await _save(ws, [LAVADORA], group_id=group_id))["success"]
    await hass.async_block_till_done()
    assert is_on(hass, LAVADORA)
    assert not is_on(hass, TERMO)

    assert (await async_ws_set(ws, 11, [ref]))["success"]
    assert (await _ws(ws, "group/delete", group_id=group_id))["success"]
    await hass.async_block_till_done()
    planner = hass.data[DOMAIN]
    assert planner.slot(DAY, 10) == planner.slot(DAY, 11) == []
    assert not is_on(hass, LAVADORA)

    # Las horas siguen funcionando tras borrar el grupo.
    await async_move_to(hass, freezer, local(2026, 11, 25, 11))
    assert not is_on(hass, LAVADORA)


@pytest.mark.freeze_time(NOW)
async def test_group_validation(hass, hass_ws_client) -> None:
    await async_setup_integration(hass)
    ws = await hass_ws_client(hass)
    unknown = "0" * 32
    for data in (
        {"entity_ids": []},
        {"entity_ids": ["lock.puerta"]},
        {"entity_ids": [TERMO], "icon": "flash"},
        {"entity_ids": [TERMO], "name": "   "},
    ):
        msg = await _ws(ws, "group/save", **{"name": "x", "icon": "mdi:flash", **data})
        assert msg["error"]["code"] == "invalid_format", data
    assert (await _save(ws, [TERMO], group_id=unknown))["error"]["code"] == "not_found"
    msg = await _ws(ws, "group/delete", group_id=unknown)
    assert msg["error"]["code"] == "not_found"
    msg = await async_ws_set(ws, 11, [f"group:{unknown}"])
    assert msg["error"]["code"] == "not_found"
    msg = await async_ws_set(ws, 11, ["group:x"])
    assert msg["error"]["code"] == "invalid_format"

    for _ in range(MAX_GROUPS):
        assert (await _save(ws, [TERMO]))["success"]
    assert (await _save(ws, [TERMO]))["error"]["code"] == "invalid_group"


@pytest.mark.freeze_time(NOW)
async def test_group_permissions(hass, hass_ws_client) -> None:
    await async_setup_integration(hass)
    admin = await hass_ws_client(hass)
    group_id = (await _save(admin, [TERMO, LAVADORA]))["result"]["group_id"]
    ref = f"group:{group_id}"

    policy = {"entities": {"entity_ids": {TERMO: True, LAVADORA: {"read": True}}}}
    ws = await _user_ws(hass, hass_ws_client, policy)
    unauthorized = (
        await async_ws_set(ws, 11, [ref]),
        await _save(ws, [TERMO], group_id=group_id),
        await _ws(ws, "group/delete", group_id=group_id),
        await _save(ws, [LAVADORA]),
    )
    assert all(m["error"]["code"] == "unauthorized" for m in unauthorized)
    assert (await _save(ws, [TERMO]))["success"]


@pytest.mark.freeze_time(NOW)
async def test_hidden(hass, hass_ws_client, hass_storage) -> None:
    entry = await async_setup_integration(hass)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/subscribe"})
    assert (await ws.receive_json())["success"]
    assert (await ws.receive_json())["event"]["hidden"] == []

    assert (await _ws(ws, "hidden/set", entity_ids=[TERMO, TERMO]))["success"]
    assert hass.data[DOMAIN].as_dict()["hidden"] == [TERMO]
    msg = await _ws(ws, "hidden/set", entity_ids=["sensor.x"])
    assert msg["error"]["code"] == "invalid_format"

    # Persisten tras recargar.
    assert await hass.config_entries.async_reload(entry.entry_id)
    assert hass_storage[DOMAIN]["data"]["hidden"] == [TERMO]
    assert hass.data[DOMAIN].hidden == [TERMO]

    policy = {"entities": {"entity_ids": {TERMO: {"read": True}}}}
    user = await _user_ws(hass, hass_ws_client, policy)
    msg = await _ws(user, "hidden/set", entity_ids=[])
    assert msg["error"]["code"] == "unauthorized"


async def test_not_loaded(hass, hass_ws_client) -> None:
    entry = await async_setup_integration(hass)
    ws = await hass_ws_client(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    for type_, data in (
        ("group/save", {"name": "x", "icon": "mdi:flash", "entity_ids": [TERMO]}),
        ("group/delete", {"group_id": "0" * 32}),
        ("hidden/set", {"entity_ids": []}),
        ("device/set", {"entity_id": TERMO}),
    ):
        assert (await _ws(ws, type_, **data))["error"]["code"] == "not_loaded"


async def test_device_customization(hass, hass_ws_client, hass_storage) -> None:
    entry = await async_setup_integration(hass)
    ws = await hass_ws_client(hass)
    planner = hass.data[DOMAIN]

    msg = await _ws(ws, "device/set", entity_id=TERMO, name=" Agua ", icon="mdi:fire")
    assert msg["success"]
    assert planner.devices == {TERMO: {"name": "Agua", "icon": "mdi:fire"}}
    assert (await _ws(ws, "device/set", entity_id=TERMO, name="", icon=None))["success"]
    assert planner.devices == {}
    assert (await _ws(ws, "device/set", entity_id=LAVADORA, icon="mdi:fire"))["success"]

    for data in (
        {"entity_id": "lock.puerta", "name": "x"},
        {"entity_id": TERMO, "icon": "fire"},
        {"entity_id": TERMO, "name": "x" * 41},
    ):
        msg = await _ws(ws, "device/set", **data)
        assert msg["error"]["code"] == "invalid_format"

    assert await hass.config_entries.async_reload(entry.entry_id)
    assert hass_storage[DOMAIN]["data"]["devices"] == {LAVADORA: {"icon": "mdi:fire"}}

    policy = {"entities": {"entity_ids": {TERMO: {"read": True}}}}
    user = await _user_ws(hass, hass_ws_client, policy)
    msg = await _ws(user, "device/set", entity_id=TERMO, name="x")
    assert msg["error"]["code"] == "unauthorized"


async def test_device_customization_limit(hass, hass_ws_client) -> None:
    await async_setup_integration(hass)
    ws = await hass_ws_client(hass)
    planner = hass.data[DOMAIN]
    planner.devices = {f"switch.s{i}": {"name": "x"} for i in range(MAX_CUSTOMIZED)}
    msg = await _ws(ws, "device/set", entity_id=TERMO, name="x")
    assert msg["error"]["code"] == "invalid_device"
    assert (await _ws(ws, "device/set", entity_id="switch.s0", name="y"))["success"]
