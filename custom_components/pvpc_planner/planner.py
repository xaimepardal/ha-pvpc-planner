"""Programación por fecha/hora y aplicación de encendidos."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, timedelta
import logging
from typing import Any
from uuid import uuid4

from homeassistant.const import STATE_ON
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    GROUP_PREFIX,
    MAX_DAYS_AHEAD,
    MAX_GROUPS,
    MAX_TEMPLATES,
    SIGNAL_UPDATED,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .rules import RULES, Price, parse_prices

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
        # Nombre/icono propios del panel: {"switch.termo": {"name": ..., "icon": ...}}
        self.devices: dict[str, dict[str, str]] = {}
        # {"<id>": {"rule": "cheapest", "params": {...}, "targets": [...]}}
        self._templates: dict[str, dict[str, Any]] = {}
        # Horas que marcan las plantillas, con la forma de _schedule. Se calcula
        # con los precios publicados y no se guarda: no pisa lo marcado a mano.
        self._auto: dict[str, dict[str, list[str]]] = {}
        # Entidades encendidas por el planner en la hora en curso.
        self._active: set[str] = set()
        self._unsubs: list = []

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self._schedule = data.get("schedule", {})
        self._active = set(data.get("active", []))
        self._groups = data.get("groups", {})
        self.hidden = data.get("hidden", [])
        self.devices = data.get("devices", {})
        self._templates = data.get("templates", {})
        self._refresh_auto()
        self._unsubs += [
            async_track_time_change(self.hass, self._async_tick, minute=0, second=0),
            async_track_state_change_event(
                self.hass, self.price_entity, self._async_prices_changed
            ),
        ]
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
            "devices": self.devices,
            "templates": self._templates,
            "auto": self._auto,
            "rules": [rule.as_dict() for rule in RULES.values()],
        }

    def template(self, template_id: str) -> dict[str, Any] | None:
        return self._templates.get(template_id)

    def slot(self, day: date, hour: int) -> list[str]:
        return self._schedule.get(day.isoformat(), {}).get(str(hour), [])

    def auto_slot(self, day: date, hour: int) -> list[str]:
        return self._auto.get(day.isoformat(), {}).get(str(hour), [])

    def _wanted(self, day: date, hour: int) -> set[str]:
        """Lo marcado a mano más lo que marquen las plantillas."""
        return {*self.slot(day, hour), *self.auto_slot(day, hour)}

    async def async_set_slot(self, day: date, hour: int, targets: list[str]) -> None:
        now = dt_util.now()
        if day < now.date() or (day == now.date() and hour < now.hour):
            raise ValueError("Cannot schedule a past hour")
        if day > now.date() + timedelta(days=MAX_DAYS_AHEAD):
            raise ValueError("Only today or tomorrow can be scheduled")

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
        for tid, tpl in list(self._templates.items()):
            if ref in tpl["targets"]:
                tpl["targets"].remove(ref)
                if not tpl["targets"]:
                    del self._templates[tid]
        self._refresh_auto()
        self._changed()
        await self.async_apply()

    async def async_save_template(
        self,
        template_id: str | None,
        rules: list[dict[str, Any]],
        targets: list[str],
    ) -> str:
        if template_id is None:
            if len(self._templates) >= MAX_TEMPLATES:
                raise ValueError(f"Máximo {MAX_TEMPLATES} plantillas")
            template_id = uuid4().hex
        self._templates[template_id] = {
            "rules": rules,
            "targets": sorted(set(targets)),
        }
        await self._async_update_auto(save=True)
        return template_id

    async def async_delete_template(self, template_id: str) -> None:
        del self._templates[template_id]
        await self._async_update_auto(save=True)

    async def _async_prices_changed(self, _: Event[EventStateChangedData]) -> None:
        await self._async_update_auto(save=False)

    async def _async_update_auto(self, save: bool) -> None:
        """Recalcula _auto; aplica solo si cambia la hora en curso."""
        now = dt_util.now()
        old, before = self._auto, self.auto_slot(now.date(), now.hour)
        self._refresh_auto()
        if save:
            self._changed()
        elif self._auto != old:
            async_dispatcher_send(self.hass, SIGNAL_UPDATED)
        if self.auto_slot(now.date(), now.hour) != before:
            await self.async_apply(now)

    @callback
    def _refresh_auto(self) -> None:
        """Recalcula _auto con los precios de hoy y mañana que haya publicados."""
        self._auto = {}
        if not self._templates:
            return
        for day, prices in self.day_prices().items():
            slots: dict[str, set[str]] = {}
            for tpl in self._templates.values():
                for hour in self._template_hours(tpl, prices):
                    slots.setdefault(str(hour), set()).update(tpl["targets"])
            if slots:
                self._auto[day.isoformat()] = {h: sorted(t) for h, t in slots.items()}

    @callback
    def day_prices(self) -> dict[date, list[Price]]:
        """Precios publicados de hoy en adelante, por día."""
        state = self.hass.states.get(self.price_entity)
        if state is None:
            return {}
        # Los atributos price_XXh son del día de su última actualización, no de
        # hoy: justo tras medianoche aún pueden ser los de ayer.
        base = dt_util.as_local(state.last_updated).date()
        today = dt_util.now().date()
        out = {}
        for offset in (0, 1):
            day = base + timedelta(days=offset)
            if day >= today and (prices := parse_prices(state.attributes, offset)):
                out[day] = prices
        return out

    @staticmethod
    def _template_hours(tpl: dict[str, Any], prices: list[Price]) -> set[int]:
        """Horas de cualquiera de sus reglas (O lógico)."""
        hours: set[int] = set()
        for item in tpl["rules"]:
            # Una regla retirada en otra versión se ignora.
            if rule := RULES.get(item["rule"]):
                hours |= rule.hours(prices, item["params"])
        return hours

    @callback
    def set_hidden(self, entity_ids: list[str]) -> None:
        self.hidden = sorted(set(entity_ids))
        self._changed()

    @callback
    def set_device(self, entity_id: str, name: str | None, icon: str | None) -> None:
        if custom := {k: v for k, v in (("name", name), ("icon", icon)) if v}:
            self.devices[entity_id] = custom
        else:
            self.devices.pop(entity_id, None)
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
        if target in self._wanted(now.date(), now.hour):
            await self.async_apply(now)

    async def _async_tick(self, _: Any = None) -> None:
        today = dt_util.now().date().isoformat()
        old = [d for d in self._schedule if d < today]
        for d in old:
            del self._schedule[d]
        if old:
            self._changed()
        # Al cambiar de día, _auto pierde el anterior.
        before = self._auto
        self._refresh_auto()
        if self._auto != before:
            async_dispatcher_send(self.hass, SIGNAL_UPDATED)
        await self.async_apply()

    async def async_apply(self, now: datetime | None = None) -> None:
        now = now or dt_util.now()
        wanted = self.entities(self._wanted(now.date(), now.hour))
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
            "devices": self.devices,
            "templates": self._templates,
        }
