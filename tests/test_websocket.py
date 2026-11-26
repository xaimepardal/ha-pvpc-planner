"""Permisos y validación de los comandos websocket."""

from datetime import date

from homeassistant.auth.models import Group
from homeassistant.auth.permissions.system_policies import USER_POLICY
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockUser

from .common import LAVADORA, NOW, TERMO, async_setup_integration, async_ws_set, is_on

DAY = date(2026, 11, 25)


async def _user_token(hass: HomeAssistant, policy: dict = USER_POLICY) -> str:
    """Token de un usuario no administrador con la política dada."""
    group = Group(name="usuarios", policy=policy)
    user = MockUser(groups=[group]).add_to_hass(hass)
    refresh = await hass.auth.async_create_refresh_token(user, "https://example.com/")
    return hass.auth.async_create_access_token(refresh)


@pytest.mark.freeze_time(NOW)
async def test_non_admin_user_can_plan(hass, hass_ws_client) -> None:
    await async_setup_integration(hass)
    ws = await hass_ws_client(hass, await _user_token(hass))
    assert (await async_ws_set(ws, 10, [TERMO]))["success"]
    await hass.async_block_till_done()
    assert is_on(hass, TERMO)


@pytest.mark.freeze_time(NOW)
async def test_read_only_user_cannot_plan(
    hass, hass_ws_client, hass_read_only_access_token
) -> None:
    await async_setup_integration(hass)
    ws = await hass_ws_client(hass, hass_read_only_access_token)

    await ws.send_json_auto_id({"type": "pvpc_planner/subscribe"})
    assert (await ws.receive_json())["success"]

    msg = await async_ws_set(ws, 11, [TERMO])
    assert msg["error"]["code"] == "unauthorized"
    assert hass.data["pvpc_planner"].slot(DAY, 11) == []


@pytest.mark.freeze_time(NOW)
async def test_entity_permissions_on_add_and_remove(hass, hass_ws_client) -> None:
    await async_setup_integration(hass)
    admin = await hass_ws_client(hass)
    assert (await async_ws_set(admin, 11, [LAVADORA]))["success"]

    policy = {"entities": {"entity_ids": {TERMO: True, LAVADORA: {"read": True}}}}
    ws = await hass_ws_client(hass, await _user_token(hass, policy))

    # Puede añadir TERMO sin tocar LAVADORA, pero no quitar ni añadir LAVADORA.
    assert (await async_ws_set(ws, 11, [LAVADORA, TERMO]))["success"]
    assert (await async_ws_set(ws, 11, [TERMO]))["error"]["code"] == "unauthorized"
    assert (await async_ws_set(ws, 12, [LAVADORA]))["error"]["code"] == "unauthorized"
    assert hass.data["pvpc_planner"].slot(DAY, 11) == [LAVADORA, TERMO]


@pytest.mark.freeze_time(NOW)
async def test_rejects_unsupported_domain(hass, hass_ws_client) -> None:
    await async_setup_integration(hass)
    ws = await hass_ws_client(hass)
    msg = await async_ws_set(ws, 11, [TERMO, "lock.puerta"])
    assert msg["error"]["code"] == "invalid_entity"
    assert hass.data["pvpc_planner"].slot(DAY, 11) == []
