"""Utilidades compartidas por los tests."""

from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.pvpc_planner.const import CONF_PRICE_ENTITY, DOMAIN

TERMO = "input_boolean.termo"
LAVADORA = "input_boolean.lavadora"

# 10:30 en Madrid. Con freeze_time el token de acceso y los temporizadores se
# crean ya con esa hora; tras avanzar más de 30 min el token caduca y HA cierra
# el websocket.
NOW = "2026-11-25 09:30:00+00:00"


def local(*args: int, fold: int = 0) -> datetime:
    return datetime(*args, tzinfo=dt_util.get_default_time_zone(), fold=fold)


async def async_setup_integration(
    hass: HomeAssistant,
    hass_storage: dict[str, Any] | None = None,
    stored: dict[str, Any] | None = None,
    initial_on: tuple[str, ...] = (),
) -> MockConfigEntry:
    await hass.config.async_set_time_zone("Europe/Madrid")
    if stored is not None:
        hass_storage[DOMAIN] = {"version": 1, "key": DOMAIN, "data": stored}
    assert await async_setup_component(
        hass,
        "input_boolean",
        {
            "input_boolean": {
                e.split(".")[1]: {"initial": e in initial_on} for e in (TERMO, LAVADORA)
            }
        },
    )
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_PRICE_ENTITY: "sensor.pvpc"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def async_move_to(hass: HomeAssistant, freezer, when: datetime) -> None:
    freezer.move_to(dt_util.as_utc(when))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


def is_on(hass: HomeAssistant, entity_id: str) -> bool:
    return hass.states.get(entity_id).state == "on"


async def async_ws_set(ws, hour: int, ids: list[str], day: str = "2026-11-25") -> dict:
    await ws.send_json_auto_id(
        {"type": f"{DOMAIN}/set", "date": day, "hour": hour, "entity_ids": ids}
    )
    while (msg := await ws.receive_json())["type"] == "event":
        pass
    return msg
