"""Entidades image: contenido, caché, refresco y autenticación."""

from datetime import date
from io import BytesIO
from unittest.mock import patch

from PIL import Image
import pytest

from custom_components.pvpc_planner import PLATFORMS, image as image_mod
from custom_components.pvpc_planner.const import DOMAIN
from custom_components.pvpc_planner.image import build_table, price_levels

from .common import (
    LAVADORA,
    NOW,
    TERMO,
    async_move_to,
    async_setup_integration,
    local,
)

TODAY = date(2026, 11, 25)
TOMORROW = date(2026, 11, 26)
IMAGES = ("image.pvpc_planner_today", "image.pvpc_planner_tomorrow")


def _prices(tomorrow: bool = False) -> dict:
    attrs = {f"price_{h:02d}h": 0.1 + h / 100 for h in range(24)}
    if tomorrow:
        attrs |= {f"price_next_day_{h:02d}h": 0.3 - h / 100 for h in range(24)}
    return attrs


async def _png(client, entity_id: str) -> Image.Image:
    resp = await client.get(f"/api/image_proxy/{entity_id}")
    assert resp.status == 200
    assert resp.content_type == "image/png"
    return Image.open(BytesIO(await resp.read()))


@pytest.mark.freeze_time(NOW)
async def test_images_served_with_auth(hass, hass_client, hass_client_no_auth) -> None:
    hass.states.async_set("sensor.pvpc", "0.2", _prices(tomorrow=True))
    await async_setup_integration(hass)
    client = await hass_client()

    for entity_id in IMAGES:
        img = await _png(client, entity_id)
        assert img.size == (800, 480)
        assert img.mode == "P"

    anon = await hass_client_no_auth()
    resp = await anon.get(f"/api/image_proxy/{IMAGES[0]}")
    assert resp.status in (401, 403)
    resp = await anon.get(f"/api/image_proxy/{IMAGES[0]}?token=bad")
    assert resp.status in (401, 403)


@pytest.mark.freeze_time(NOW)
async def test_cache_and_refresh(hass, hass_client, freezer) -> None:
    hass.states.async_set("sensor.pvpc", "0.2", _prices())
    await async_setup_integration(hass)
    planner = hass.data[DOMAIN]
    client = await hass_client()
    state = hass.states.get(IMAGES[0]).state
    tomorrow_state = hass.states.get(IMAGES[1]).state

    with patch.object(image_mod, "render_png", wraps=image_mod.render_png) as render:
        await _png(client, IMAGES[0])
        await _png(client, IMAGES[0])
        assert render.call_count == 1

        # Cambiar la programación invalida la caché y cambia el estado.
        freezer.tick(1)
        await planner.async_set_slot(TODAY, 12, [TERMO])
        await hass.async_block_till_done()
        assert hass.states.get(IMAGES[0]).state != state
        await _png(client, IMAGES[0])
        assert render.call_count == 2

        # Un aviso sin cambios en lo que se dibuja no regenera.
        state = hass.states.get(IMAGES[0]).state
        hass.states.async_set("sensor.pvpc", "0.3", _prices())
        await hass.async_block_till_done()
        assert hass.states.get(IMAGES[0]).state == state

        # Los precios de mañana llegan: cambia solo la de mañana.
        hass.states.async_set("sensor.pvpc", "0.3", _prices(tomorrow=True))
        await hass.async_block_till_done()
        assert hass.states.get(IMAGES[0]).state == state
        assert hass.states.get(IMAGES[1]).state != tomorrow_state

        # Cambio de hora: la hora en curso pasa a ser otra.
        await async_move_to(hass, freezer, local(2026, 11, 25, 11))
        assert hass.states.get(IMAGES[0]).state != state


@pytest.mark.freeze_time(NOW)
async def test_stale_render_not_cached(hass) -> None:
    hass.states.async_set("sensor.pvpc", "0.2", _prices())
    await async_setup_integration(hass)
    entity = next(e for e in hass.data["image"].entities if e.entity_id == IMAGES[0])
    old = entity._table

    def render(table):
        entity._table = build_table(hass, hass.data[DOMAIN], True)
        return b"old"

    with patch.object(image_mod, "render_png", side_effect=render):
        assert await entity.async_image() == b"old"
    assert entity._png is None
    assert entity._table is not old


@pytest.mark.freeze_time(NOW)
async def test_build_table(hass) -> None:
    hass.states.async_set("sensor.pvpc", "0.2", _prices(tomorrow=True))
    hass.states.async_set(
        "switch.raro", "off", {"icon": "mdi:heat-pump", "friendly_name": "Raro"}
    )
    await async_setup_integration(hass)
    hass.config.language = "gl"
    planner = hass.data[DOMAIN]
    group_id = await planner.async_save_group(None, "Cocina", "", [LAVADORA])
    planner.set_device(TERMO, "Termo", "mdi:water-boiler")
    await planner.async_set_slot(
        TODAY,
        12,
        [TERMO, LAVADORA, f"group:{group_id}", "switch.raro", "light.gone"],
    )
    await planner.async_save_template(
        None,
        [
            {
                "rule": "cheapest",
                "params": {
                    "hours": 1,
                    "after_cheapest": False,
                    "second_if_alone": False,
                },
            }
        ],
        [LAVADORA],
    )

    table = build_table(hass, planner, False)
    assert (table.day, table.today, table.lang) == (TODAY, True, "gl")
    cells = {c.hour: c for c in table.cells}
    assert cells[9].past
    assert not cells[9].now
    assert cells[10].now
    assert not cells[10].past
    assert cells[0].level == "cheap"
    assert cells[0].auto
    assert cells[23].level == "expensive"
    assert cells[12].level is None
    assert [(d.name, d.icon) for d in cells[12].devices] == [
        ("Cocina", "mdi:devices"),
        (LAVADORA, "mdi:toggle-switch-outline"),
        ("Termo", "mdi:water-boiler"),
        ("light.gone", "mdi:lightbulb"),
        ("Raro", "mdi:heat-pump"),
    ]
    tomorrow = build_table(hass, planner, True)
    assert tomorrow.day == TOMORROW
    assert not any(c.past or c.now for c in tomorrow.cells)
    assert tomorrow.cells[23].level == "cheap"

    # Grupo borrado entre medias y sin sensor de precios.
    planner._groups.clear()
    assert (
        build_table(hass, planner, False).cells[12].devices[0].name.startswith("group:")
    )
    hass.states.async_remove("sensor.pvpc")
    empty = build_table(hass, planner, False)
    assert empty.cells == ()


def test_price_levels() -> None:
    assert price_levels([]) == {}
    # Con menos de 12 horas, las baratas tienen prioridad.
    levels = price_levels([(h, float(h)) for h in range(8)])
    assert [levels[h] for h in range(8)] == ["cheap"] * 6 + ["expensive"] * 2
    # A igual precio, la hora más temprana es la más barata.
    levels = price_levels([(h, 1.0) for h in range(24)])
    assert {h for h, v in levels.items() if v == "cheap"} == set(range(6))
    assert {h for h, v in levels.items() if v == "expensive"} == set(range(18, 24))


@pytest.mark.freeze_time(NOW)
async def test_unload_fails_if_platform_fails(hass) -> None:
    entry = await async_setup_integration(hass)
    with patch.object(
        hass.config_entries, "async_unload_platforms", return_value=False
    ):
        assert not await hass.config_entries.async_unload(entry.entry_id)
    assert DOMAIN in hass.data
    assert await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    await hass.data.pop(DOMAIN).async_unload()
