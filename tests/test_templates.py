"""Plantillas automáticas: cálculo, aplicación, permisos y validación."""

from datetime import date

from homeassistant.auth.models import Group
import pytest
from pytest_homeassistant_custom_component.common import MockUser

from custom_components.pvpc_planner.const import DOMAIN, MAX_TEMPLATES

from .common import (
    LAVADORA,
    NOW,
    TERMO,
    async_move_to,
    async_setup_integration,
    is_on,
    local,
)

TODAY = date(2026, 11, 25)
CHEAPEST_2 = [
    {
        "rule": "cheapest",
        "params": {"hours": 2, "after_cheapest": False, "second_if_alone": False},
    }
]


def _prices(cheap_today: tuple[int, ...], cheap_tomorrow: tuple[int, ...] = ()):
    attrs = {f"price_{h:02d}h": 0.01 if h in cheap_today else 0.2 for h in range(24)}
    if cheap_tomorrow:
        attrs |= {
            f"price_next_day_{h:02d}h": 0.01 if h in cheap_tomorrow else 0.2
            for h in range(24)
        }
    return attrs


async def _ws(ws, type_: str, **data) -> dict:
    await ws.send_json_auto_id({"type": f"{DOMAIN}/{type_}", **data})
    while (msg := await ws.receive_json())["type"] == "event":
        pass
    return msg


async def _save(ws, targets, rules=None, **data) -> dict:
    if rules is None:
        rules = [{"rule": "cheapest", "params": {"hours": 2}}]
    return await _ws(ws, "template/save", rules=rules, targets=targets, **data)


async def _user_ws(hass, hass_ws_client, policy: dict):
    user = MockUser(groups=[Group(name="u", policy=policy)]).add_to_hass(hass)
    refresh = await hass.auth.async_create_refresh_token(user, "https://example.com/")
    return await hass_ws_client(hass, hass.auth.async_create_access_token(refresh))


@pytest.mark.freeze_time(NOW)
async def test_template_marks_and_applies(hass, hass_ws_client, freezer) -> None:
    hass.states.async_set("sensor.pvpc", "0.2", _prices((10, 11)))
    await async_setup_integration(hass)
    ws = await hass_ws_client(hass)
    planner = hass.data[DOMAIN]

    msg = await _save(ws, [TERMO])
    assert msg["success"]
    tid = msg["result"]["template_id"]
    await hass.async_block_till_done()
    assert planner.as_dict()["auto"] == {"2026-11-25": {"10": [TERMO], "11": [TERMO]}}
    # Afecta a la hora en curso: se aplica al momento.
    assert is_on(hass, TERMO)

    # Convive con lo marcado a mano: se suman.
    await planner.async_set_slot(TODAY, 12, [LAVADORA])
    await async_move_to(hass, freezer, local(2026, 11, 25, 11))
    assert is_on(hass, TERMO)
    await async_move_to(hass, freezer, local(2026, 11, 25, 12))
    assert not is_on(hass, TERMO)
    assert is_on(hass, LAVADORA)

    # Al publicarse los de mañana se calculan sin tocar nada más.
    hass.states.async_set("sensor.pvpc", "0.2", _prices((10, 11), (3, 4)))
    await hass.async_block_till_done()
    assert planner.as_dict()["auto"]["2026-11-26"] == {"3": [TERMO], "4": [TERMO]}

    await planner.async_delete_template(tid)
    assert planner.as_dict()["auto"] == {}


@pytest.mark.freeze_time(NOW)
async def test_edit_and_price_change_apply_now(hass, hass_ws_client) -> None:
    hass.states.async_set("sensor.pvpc", "0.2", _prices((3, 4)))
    await async_setup_integration(hass)
    ws = await hass_ws_client(hass)
    tid = (await _save(ws, [TERMO]))["result"]["template_id"]
    assert not is_on(hass, TERMO)

    hass.states.async_set("sensor.pvpc", "0.2", _prices((10, 4)))
    await hass.async_block_till_done()
    assert is_on(hass, TERMO)

    assert (await _save(ws, [LAVADORA], template_id=tid))["success"]
    await hass.async_block_till_done()
    assert is_on(hass, LAVADORA)
    assert not is_on(hass, TERMO)


@pytest.mark.freeze_time("2026-11-25 23:00:10+00:00")
async def test_after_midnight_with_old_attributes(hass) -> None:
    """A las 00:00 el sensor aún tiene los atributos de ayer."""
    hass.states.async_set("sensor.pvpc", "0.2", _prices((5,), (0, 1)))
    await async_setup_integration(hass)
    hass.states.async_set("sensor.pvpc", "0.3", _prices((5,), (0, 1)))
    planner = hass.data[DOMAIN]
    # El estado lleva fecha de hoy (00:00:10): se cuadra con last_updated.
    await planner.async_save_template(None, CHEAPEST_2, [TERMO])
    await hass.async_block_till_done()
    assert set(planner.as_dict()["auto"]) == {"2026-11-26", "2026-11-27"}


@pytest.mark.freeze_time("2026-11-25 22:59:50+00:00")
async def test_midnight_tick_uses_next_day_prices(hass, freezer) -> None:
    hass.states.async_set("sensor.pvpc", "0.2", _prices((5,), (0, 1)))
    await async_setup_integration(hass)
    planner = hass.data[DOMAIN]
    await planner.async_save_template(None, CHEAPEST_2, [TERMO])
    await async_move_to(hass, freezer, local(2026, 11, 26, 0))
    assert planner.as_dict()["auto"] == {"2026-11-26": {"0": [TERMO], "1": [TERMO]}}
    assert is_on(hass, TERMO)


@pytest.mark.freeze_time(NOW)
async def test_without_prices_and_persistence(hass, hass_ws_client, hass_storage):
    entry = await async_setup_integration(hass)
    ws = await hass_ws_client(hass)
    assert (await _save(ws, [TERMO]))["success"]
    planner = hass.data[DOMAIN]
    assert planner.as_dict()["auto"] == {}
    assert [r["id"] for r in planner.as_dict()["rules"]] == [
        "cheapest",
        "window",
        "negative",
    ]

    # Una regla retirada en otra versión se ignora.
    hass.states.async_set("sensor.pvpc", "0.2", _prices((11,)))
    assert await hass.config_entries.async_reload(entry.entry_id)
    stored = hass_storage[DOMAIN]["data"]["templates"]
    (tpl,) = stored.values()
    # Se guarda con los valores por defecto ya puestos.
    assert tpl["rules"] == CHEAPEST_2
    tpl["rules"].append({"rule": "gone", "params": {}})
    assert await hass.config_entries.async_reload(entry.entry_id)
    assert set(hass.data[DOMAIN].as_dict()["auto"]["2026-11-25"]) == {"0", "11"}


@pytest.mark.freeze_time(NOW)
async def test_group_targets(hass, hass_ws_client) -> None:
    hass.states.async_set("sensor.pvpc", "0.2", _prices((10, 11)))
    await async_setup_integration(hass)
    ws = await hass_ws_client(hass)
    planner = hass.data[DOMAIN]
    gid = (
        await _ws(ws, "group/save", name="A", icon="mdi:flash", entity_ids=[LAVADORA])
    )["result"]["group_id"]
    ref = f"group:{gid}"
    assert (await _save(ws, [ref]))["success"]
    assert (await _save(ws, [ref, TERMO]))["success"]
    await hass.async_block_till_done()
    assert is_on(hass, LAVADORA)

    # Editar el grupo de una plantilla activa se aplica al momento.
    assert (
        await _ws(
            ws,
            "group/save",
            group_id=gid,
            name="A",
            icon="mdi:flash",
            entity_ids=[LAVADORA, TERMO],
        )
    )["success"]

    # Al borrar el grupo se quita de las plantillas; las que se quedan vacías, fuera.
    assert (await _ws(ws, "group/delete", group_id=gid))["success"]
    templates = planner.as_dict()["templates"]
    assert [t["targets"] for t in templates.values()] == [[TERMO]]
    await hass.async_block_till_done()
    assert not is_on(hass, LAVADORA)
    assert is_on(hass, TERMO)


@pytest.mark.freeze_time(NOW)
async def test_template_validation(hass, hass_ws_client) -> None:
    await async_setup_integration(hass)
    ws = await hass_ws_client(hass)
    unknown = "0" * 32
    for rules, targets in (
        ([], [TERMO]),
        (CHEAPEST_2, []),
        (CHEAPEST_2, ["lock.puerta"]),
        ([{"rule": "nope"}], [TERMO]),
        ([{"rule": "cheapest", "params": {"hours": 30}}], [TERMO]),
        ([{"rule": "window", "params": {"from": 10, "to": 9}}], [TERMO]),
        ([{"rule": "negative", "params": {"x": 1}}], [TERMO]),
        ([{"rule": "negative"}] * 11, [TERMO]),
    ):
        msg = await _save(ws, targets, rules)
        assert msg["error"]["code"] == "invalid_format", rules
    assert (await _save(ws, [f"group:{unknown}"]))["error"]["code"] == "not_found"
    msg = await _save(ws, [TERMO], template_id=unknown)
    assert msg["error"]["code"] == "not_found"
    msg = await _ws(ws, "template/delete", template_id=unknown)
    assert msg["error"]["code"] == "not_found"

    assert (await _save(ws, [TERMO], [{"rule": "negative"}]))["success"]
    for _ in range(MAX_TEMPLATES - 1):
        assert (await _save(ws, [TERMO]))["success"]
    assert (await _save(ws, [TERMO]))["error"]["code"] == "invalid_template"


@pytest.mark.freeze_time(NOW)
async def test_template_permissions(hass, hass_ws_client) -> None:
    await async_setup_integration(hass)
    admin = await hass_ws_client(hass)
    tid = (await _save(admin, [TERMO, LAVADORA]))["result"]["template_id"]

    policy = {"entities": {"entity_ids": {TERMO: True, LAVADORA: {"read": True}}}}
    ws = await _user_ws(hass, hass_ws_client, policy)
    unauthorized = (
        await _save(ws, [TERMO], template_id=tid),
        await _ws(ws, "template/delete", template_id=tid),
        await _save(ws, [LAVADORA]),
    )
    assert all(m["error"]["code"] == "unauthorized" for m in unauthorized)
    assert (await _save(ws, [TERMO]))["success"]


async def test_not_loaded(hass, hass_ws_client) -> None:
    entry = await async_setup_integration(hass)
    ws = await hass_ws_client(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    msg = await _save(ws, [TERMO])
    assert msg["error"]["code"] == "not_loaded"
    msg = await _ws(ws, "template/delete", template_id="0" * 32)
    assert msg["error"]["code"] == "not_loaded"
