"""Entidades image con la tabla de hoy y de mañana.

Se sirven por /api/image_proxy/<entity_id> con la autenticación de HA. La
imagen se genera al pedirla y se guarda hasta que cambia lo que muestra.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_FRIENDLY_NAME, ATTR_ICON, ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    DOMAIN_ICONS,
    GROUP_ICON,
    GROUP_PREFIX,
    PRICE_LEVEL_HOURS,
    SIGNAL_UPDATED,
)
from .planner import Planner
from .render import Cell, Device, Table, render_png
from .rules import Price

DEFAULT_UNIT = "€/kWh"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    planner: Planner = hass.data[DOMAIN]
    async_add_entities(
        TableImage(entry, planner, tomorrow) for tomorrow in (False, True)
    )


def price_levels(prices: list[Price]) -> dict[int, str]:
    """Hora -> "cheap"/"expensive", igual que el panel."""
    by_price = sorted(prices, key=lambda p: p[1])
    levels = {h: "cheap" for h, _ in by_price[:PRICE_LEVEL_HOURS]}
    for h, _ in by_price[max(len(by_price) - PRICE_LEVEL_HOURS, 0) :]:
        levels.setdefault(h, "expensive")
    return levels


def _device(hass: HomeAssistant, planner: Planner, target: str) -> Device:
    """Nombre e icono como en el panel: lo personalizado por delante de HA."""
    if target.startswith(GROUP_PREFIX):
        group = planner.group(target.removeprefix(GROUP_PREFIX)) or {}
        return Device(group.get("name", target), group.get("icon") or GROUP_ICON)
    custom = planner.devices.get(target, {})
    attrs = state.attributes if (state := hass.states.get(target)) else {}
    return Device(
        custom.get("name") or attrs.get(ATTR_FRIENDLY_NAME) or target,
        custom.get("icon")
        or attrs.get(ATTR_ICON)
        or DOMAIN_ICONS.get(target.split(".")[0], GROUP_ICON),
    )


@callback
def build_table(hass: HomeAssistant, planner: Planner, tomorrow: bool) -> Table:
    now = dt_util.now()
    day = now.date() + timedelta(days=tomorrow)
    prices = planner.day_prices().get(day, [])
    levels = price_levels(prices)
    cells = []
    for hour, price in prices:
        auto = planner.auto_slot(day, hour)
        # Mismo orden que el panel: lo manual y luego lo de plantillas.
        targets = dict.fromkeys([*planner.slot(day, hour), *auto])
        cells.append(
            Cell(
                hour=hour,
                price=price,
                level=levels.get(hour),
                past=not tomorrow and hour < now.hour,
                now=not tomorrow and hour == now.hour,
                auto=bool(auto),
                devices=tuple(_device(hass, planner, t) for t in targets),
            )
        )
    state = hass.states.get(planner.price_entity)
    unit = state and state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
    return Table(
        day=day,
        today=not tomorrow,
        lang=hass.config.language,
        unit=unit or DEFAULT_UNIT,
        templates=planner.has_templates,
        cells=tuple(cells),
    )


class TableImage(ImageEntity):
    _attr_has_entity_name = True
    _attr_content_type = "image/png"

    def __init__(self, entry: ConfigEntry, planner: Planner, tomorrow: bool) -> None:
        super().__init__(planner.hass)
        key = "tomorrow" if tomorrow else "today"
        self._planner = planner
        self._tomorrow = tomorrow
        self._table: Table | None = None
        self._png: bytes | None = None
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        # Id estable en inglés, sea cual sea el idioma de HA.
        self.entity_id = f"image.{DOMAIN}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="PVPC Planner",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        self._refresh(write=False)
        for unsub in (
            async_dispatcher_connect(self.hass, SIGNAL_UPDATED, self._refresh),
            async_track_state_change_event(
                self.hass, self._planner.price_entity, self._refresh
            ),
            # Hora en curso, horas pasadas y cambio de día.
            async_track_time_change(self.hass, self._refresh, minute=0, second=0),
        ):
            self.async_on_remove(unsub)

    @callback
    def _refresh(self, *_: Any, write: bool = True) -> None:
        table = build_table(self.hass, self._planner, self._tomorrow)
        if table == self._table:
            return
        self._table, self._png = table, None
        self._attr_image_last_updated = dt_util.utcnow()
        if write:
            self.async_write_ha_state()

    async def async_image(self) -> bytes | None:
        if self._png is None:
            table = self._table
            png = await self.hass.async_add_executor_job(render_png, table)
            # Si la tabla cambió mientras tanto, no se guarda la vieja.
            if table is self._table:
                self._png = png
            return png
        return self._png
