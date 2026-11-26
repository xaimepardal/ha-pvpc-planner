"""Reglas de las plantillas automáticas.

Cada regla declara sus parámetros: el backend valida con ellos y el panel
genera los desplegables, así que una regla nueva solo necesita su función,
su entrada en RULES y sus textos en el panel (rule_<id>, rule_<id>_name,
param_<key>).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import re
from typing import Any

import voluptuous as vol

type Price = tuple[int, float]
type Params = Mapping[str, Any]

_PRICE_KEY = {
    False: re.compile(r"^price_(\d{2})h(?:_d)?$"),
    True: re.compile(r"^price_next_day_(\d{2})h(?:_d)?$"),
}


def parse_prices(attrs: Mapping[str, Any], next_day: bool) -> list[Price]:
    """(hora, precio) de los atributos de pvpc_hourly_pricing, por hora.

    La hora repetida del cambio de horario ("_d") comparte franja: media de ambas.
    """
    by_hour: dict[int, list[float]] = {}
    for key, value in attrs.items():
        if (m := _PRICE_KEY[next_day].match(key)) and isinstance(value, int | float):
            by_hour.setdefault(int(m[1]), []).append(float(value))
    return [(h, sum(v) / len(v)) for h, v in sorted(by_hour.items())]


@dataclass(frozen=True, slots=True)
class IntParam:
    key: str
    min: int
    max: int
    default: int
    # "hour": el panel lo muestra como HH:00.
    unit: str | None = None

    def validator(self) -> vol.All:
        return vol.All(vol.Coerce(int), vol.Range(min=self.min, max=self.max))

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "type": "int",
            "min": self.min,
            "max": self.max,
            "default": self.default,
            "unit": self.unit,
        }


@dataclass(frozen=True, slots=True)
class BoolParam:
    key: str
    default: bool = False
    # Otro BoolParam del que depende: sin él marcado no tiene efecto.
    requires: str | None = None

    def validator(self) -> type[bool]:
        return bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "type": "bool",
            "default": self.default,
            "requires": self.requires,
        }


def _no_check(_: Params) -> None:
    return None


@dataclass(frozen=True, slots=True)
class Rule:
    id: str
    params: tuple[IntParam | BoolParam, ...]
    # Horas del día (0-23) que cumplen la regla.
    hours: Callable[[list[Price], Params], set[int]]
    # Validación entre parámetros; lanza vol.Invalid.
    check: Callable[[Params], None] = _no_check

    def validate(self, params: Mapping[str, Any]) -> dict[str, Any]:
        """Parámetros válidos con sus valores por defecto; rechaza los desconocidos."""
        out = vol.Schema(
            {vol.Optional(p.key, default=p.default): p.validator() for p in self.params}
        )(dict(params))
        self.check(out)
        return out

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.id, "params": [p.as_dict() for p in self.params]}


def _by_price(prices: list[Price]) -> list[Price]:
    # Estable: a igual precio, la hora más temprana.
    return sorted(prices, key=lambda p: p[1])


def _cheapest(prices: list[Price], params: Params) -> set[int]:
    best = _by_price(prices)[: params["hours"]]
    if not params["after_cheapest"] or not best:
        return {h for h, _ in best}
    # Solo desde la más barata en adelante; si queda sola, desde la segunda.
    start = best[0][0]
    alone = sum(h >= start for h, _ in best) == 1
    if params["second_if_alone"] and alone and len(best) > 1:
        start = best[1][0]
    return {h for h, _ in best if h >= start}


def _in_window(prices: list[Price], params: Params) -> set[int]:
    window = [p for p in prices if params["from"] <= p[0] < params["to"]]
    return {h for h, _ in _by_price(window)[: params["hours"]]}


def _check_window(params: Params) -> None:
    if params["from"] >= params["to"]:
        raise vol.Invalid("'from' must be earlier than 'to'")


def _negative(prices: list[Price], _: Params) -> set[int]:
    return {h for h, price in prices if price < 0}


RULES: dict[str, Rule] = {
    rule.id: rule
    for rule in (
        Rule(
            "cheapest",
            (
                IntParam("hours", 1, 24, 3),
                BoolParam("after_cheapest"),
                BoolParam("second_if_alone", requires="after_cheapest"),
            ),
            _cheapest,
        ),
        Rule(
            "window",
            (
                IntParam("hours", 1, 24, 1),
                IntParam("from", 0, 23, 0, "hour"),
                IntParam("to", 1, 24, 24, "hour"),
            ),
            _in_window,
            _check_window,
        ),
        Rule("negative", (), _negative),
    )
}
