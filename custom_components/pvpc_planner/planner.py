"""Programación por fecha/hora y aplicación de encendidos."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import logging
from typing import Any

from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import MAX_DAYS_AHEAD, SIGNAL_UPDATED, STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)


class Planner:
    """Entidades a encender por fecha y hora local.

    Una entidad encendida por el planner se apaga al empezar la primera hora
    en la que no esté marcada. Las que ya estaban encendidas no se adoptan.
    """

    def __init__(self, hass: HomeAssistant, price_entity: str) -> None:
        self.hass = hass
        self.price_entity = price_entity
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        # {"2026-11-25": {"13": ["switch.termo"]}}
        self._schedule: dict[str, dict[str, list[str]]] = {}
        # Entidades encendidas por el planner en la hora en curso.
        self._active: set[str] = set()
        self._unsubs: list = []

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self._schedule = data.get("schedule", {})
        self._active = set(data.get("active", []))
        self._unsubs.append(
            async_track_time_change(self.hass, self._async_tick, minute=0, second=0)
        )
        # Tras un reinicio, recupera el estado de la hora en curso.
        self._unsubs.append(async_at_started(self.hass, self._async_tick))

    @callback
    def async_unload(self) -> None:
        while self._unsubs:
            self._unsubs.pop()()

    def as_dict(self) -> dict[str, Any]:
        return {"price_entity": self.price_entity, "schedule": self._schedule}

    def slot(self, day: date, hour: int) -> list[str]:
        return self._schedule.get(day.isoformat(), {}).get(str(hour), [])

    async def async_set_slot(
        self, day: date, hour: int, entity_ids: list[str]
    ) -> None:
        now = dt_util.now()
        if day < now.date() or (day == now.date() and hour < now.hour):
            raise ValueError("No se puede programar una hora pasada")
        if day > now.date() + timedelta(days=MAX_DAYS_AHEAD):
            raise ValueError("Solo se puede programar hoy o mañana")

        key = day.isoformat()
        slots = self._schedule.setdefault(key, {})
        if entity_ids:
            slots[str(hour)] = sorted(set(entity_ids))
        else:
            slots.pop(str(hour), None)
        if not slots:
            del self._schedule[key]
        self._changed()

        if day == now.date() and hour == now.hour:
            await self.async_apply()

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
        wanted = set(self.slot(now.date(), now.hour))
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
        self._store.async_delay_save(
            lambda: {"schedule": self._schedule, "active": sorted(self._active)}, 1
        )
