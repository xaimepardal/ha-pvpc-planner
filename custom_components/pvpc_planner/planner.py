"""Programación por fecha/hora y aplicación de encendidos."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, timedelta
import logging
from typing import Any
from uuid import uuid4

from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    GROUP_PREFIX,
    MAX_DAYS_AHEAD,
    MAX_GROUPS,
    SIGNAL_UPDATED,
    STORAGE_KEY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


class Planner:
    """Entidades o grupos a encender por fecha y hora local.

    Una entidad encendida por el planner se apaga al empezar la primera hora
    en la que no esté marcada. Las que ya estaban encendidas no se adoptan.
    """

    def __init__(self, hass: HomeAssistant, price_entity: str) -> None:
        self.hass = hass
        self.price_entity = price_entity
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        # {"2026-11-25": {"13": ["switch.termo", "group:<id>"]}}
        self._schedule: dict[str, dict[str, list[str]]] = {}
        # {"<id>": {"name": ..., "icon": "mdi:...", "entity_ids": [...]}}
        self._groups: dict[str, dict[str, Any]] = {}
        # Entidades que el panel no ofrece al elegir dispositivos.
        self.hidden: list[str] = []
        # Entidades encendidas por el planner en la hora en curso.
        self._active: set[str] = set()
        self._unsubs: list = []

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self._schedule = data.get("schedule", {})
        self._active = set(data.get("active", []))
        self._groups = data.get("groups", {})
        self.hidden = data.get("hidden", [])
        self._unsubs.append(
            async_track_time_change(self.hass, self._async_tick, minute=0, second=0)
        )
        # Tras un reinicio, recupera el estado de la hora en curso.
        self._unsubs.append(async_at_started(self.hass, self._async_tick))

    async def async_unload(self) -> None:
        while self._unsubs:
            self._unsubs.pop()()
        # Sin esperar al guardado diferido: un reload inmediato leería datos viejos.
        await self._store.async_save(self._data())

    def group(self, group_id: str) -> dict[str, Any] | None:
        return self._groups.get(group_id)

    def entities(self, targets: Iterable[str]) -> set[str]:
        """Expande los grupos de `targets` a sus entidades."""
        out: set[str] = set()
        for target in targets:
            if target.startswith(GROUP_PREFIX):
                group = self._groups.get(target.removeprefix(GROUP_PREFIX), {})
                out.update(group.get("entity_ids", []))
            else:
                out.add(target)
        return out

    def as_dict(self) -> dict[str, Any]:
        return {
            "price_entity": self.price_entity,
            "schedule": self._schedule,
            "groups": self._groups,
            "hidden": self.hidden,
        }

    def slot(self, day: date, hour: int) -> list[str]:
        return self._schedule.get(day.isoformat(), {}).get(str(hour), [])

    async def async_set_slot(self, day: date, hour: int, targets: list[str]) -> None:
        now = dt_util.now()
        if day < now.date() or (day == now.date() and hour < now.hour):
            raise ValueError("No se puede programar una hora pasada")
        if day > now.date() + timedelta(days=MAX_DAYS_AHEAD):
            raise ValueError("Solo se puede programar hoy o mañana")

        self._put_slot(day.isoformat(), str(hour), targets)
        self._changed()

        if day == now.date() and hour == now.hour:
            await self.async_apply()

    async def async_save_group(
        self, group_id: str | None, name: str, icon: str, entity_ids: list[str]
    ) -> str:
        if group_id is None:
            if len(self._groups) >= MAX_GROUPS:
                raise ValueError(f"Máximo {MAX_GROUPS} grupos")
            group_id = uuid4().hex
        self._groups[group_id] = {
            "name": name,
            "icon": icon,
            "entity_ids": sorted(set(entity_ids)),
        }
        self._changed()
        await self._async_apply_if_current(GROUP_PREFIX + group_id)
        return group_id

    async def async_delete_group(self, group_id: str) -> None:
        del self._groups[group_id]
        ref = GROUP_PREFIX + group_id
        for key, slots in list(self._schedule.items()):
            for hour, targets in list(slots.items()):
                if ref in targets:
                    self._put_slot(key, hour, [t for t in targets if t != ref])
        self._changed()
        await self.async_apply()

    @callback
    def set_hidden(self, entity_ids: list[str]) -> None:
        self.hidden = sorted(set(entity_ids))
        self._changed()

    def _put_slot(self, key: str, hour: str, targets: list[str]) -> None:
        slots = self._schedule.setdefault(key, {})
        if targets:
            slots[hour] = sorted(set(targets))
        else:
            slots.pop(hour, None)
        if not slots:
            del self._schedule[key]

    async def _async_apply_if_current(self, target: str) -> None:
        now = dt_util.now()
        if target in self.slot(now.date(), now.hour):
            await self.async_apply(now)

    async def _async_tick(self, _: Any = None) -> None:
        today = dt_util.now().date().isoformat()
        old = [d for d in self._schedule if d < today]
        for d in old:
            del self._schedule[d]
        if old:
            self._changed()
        await self.async_apply()

    async def async_apply(self, now: datetime | None = None) -> None:
        now = now or dt_util.now()
        wanted = self.entities(self.slot(now.date(), now.hour))
        to_off = [e for e in self._active - wanted if self.hass.states.get(e)]
        to_on = [
            e
            for e in wanted
            if (state := self.hass.states.get(e)) and state.state != STATE_ON
        ]
        self._active = (self._active & wanted) | set(to_on)
        self._save()
        await self._async_call("turn_off", to_off)
        await self._async_call("turn_on", to_on)

    async def _async_call(self, service: str, entity_ids: list[str]) -> None:
        by_domain: dict[str, list[str]] = {}
        for entity_id in entity_ids:
            by_domain.setdefault(entity_id.split(".")[0], []).append(entity_id)
        for domain, ids in by_domain.items():
            try:
                await self.hass.services.async_call(
                    domain, service, {"entity_id": ids}, blocking=True
                )
            except HomeAssistantError as err:
                _LOGGER.error("Error en %s.%s de %s: %s", domain, service, ids, err)

    @callback
    def _changed(self) -> None:
        self._save()
        async_dispatcher_send(self.hass, SIGNAL_UPDATED)

    @callback
    def _save(self) -> None:
        self._store.async_delay_save(self._data, 1)

    def _data(self) -> dict[str, Any]:
        return {
            "schedule": self._schedule,
            "active": sorted(self._active),
            "groups": self._groups,
            "hidden": self.hidden,
        }
