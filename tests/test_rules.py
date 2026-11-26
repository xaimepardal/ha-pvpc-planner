"""Reglas de las plantillas y caso de aceptación: la automatización del calentador."""

import random

import pytest
import voluptuous as vol

from custom_components.pvpc_planner.rules import RULES, parse_prices

# La automatización YAML del calentador, con desplegables.
CALENTADOR = [
    {"rule": "cheapest", "hours": 6, "after_cheapest": True, "second_if_alone": True},
    {"rule": "window", "hours": 1, "from": 12, "to": 16},
    {"rule": "negative"},
]


def _hours(rules: list[dict], prices: dict[int, float]) -> set[int]:
    out: set[int] = set()
    for item in rules:
        rule = RULES[item["rule"]]
        params = rule.validate({k: v for k, v in item.items() if k != "rule"})
        out |= rule.hours(sorted(prices.items()), params)
    return out


def _yaml_calentador(prices: dict[int, float]) -> set[int]:
    """Traducción literal de las tres condiciones Jinja de la automatización."""
    on = set()
    for now in range(24):
        p = prices.get(now)
        negative = p is not None and p < 0

        d = [{"h": h, "p": prices[h]} for h in range(24) if h in prices]
        baratas = sorted(d, key=lambda x: x["p"])[:6]
        cheap = False
        if baratas:
            ini = baratas[0]["h"]
            if len([b for b in baratas if b["h"] >= ini]) == 1 and len(baratas) > 1:
                ini = baratas[1]["h"]
            cheap = now in [b["h"] for b in baratas if b["h"] >= ini]

        m_h = m_p = None
        for h in range(12, 16):
            q = prices.get(h)
            if q is not None and (m_p is None or q < m_p):
                m_h, m_p = h, q
        if negative or cheap or now == m_h:
            on.add(now)
    return on


def _profiles():
    flat = dict.fromkeys(range(24), 0.1)
    cheapest_last = {h: 0.2 - h / 1000 for h in range(24)}  # la más barata, las 23
    valley = {h: 0.05 if h < 7 else 0.15 for h in range(24)}
    solar = {h: -0.01 if 11 <= h <= 15 else 0.12 for h in range(24)}
    yield from (flat, cheapest_last, valley, solar, {}, {3: 0.1, 20: 0.05})
    rnd = random.Random(1)
    for _ in range(300):
        # Pocos valores distintos para forzar empates y negativos.
        yield {h: rnd.choice((-0.02, 0, 0.05, 0.08, 0.1, 0.2)) for h in range(24)}


@pytest.mark.parametrize("prices", list(_profiles()))
def test_calentador_matches_yaml(prices: dict[int, float]) -> None:
    assert _hours(CALENTADOR, prices) == _yaml_calentador(prices)


def test_cheapest_variants() -> None:
    # Más baratas: 23, 2, 22, 1 (en ese orden).
    prices = dict.fromkeys(range(24), 0.3) | {23: 0.01, 2: 0.02, 22: 0.03, 1: 0.04}
    base = {"rule": "cheapest", "hours": 4}
    assert _hours([base], prices) == {1, 2, 22, 23}
    assert _hours([base | {"after_cheapest": True}], prices) == {23}
    both = base | {"after_cheapest": True, "second_if_alone": True}
    assert _hours([both], prices) == {2, 22, 23}


def test_window() -> None:
    prices = {h: h / 100 for h in range(24)}
    assert _hours([{"rule": "window", "hours": 2, "from": 20, "to": 24}], prices) == {
        20,
        21,
    }
    assert _hours([{"rule": "window", "from": 5, "to": 6}], {}) == set()


@pytest.mark.parametrize(
    ("rule", "params"),
    [
        ("cheapest", {"hours": 0}),
        ("cheapest", {"hours": 25}),
        ("cheapest", {"after_cheapest": "yes"}),
        ("cheapest", {"unknown": 1}),
        ("window", {"from": 16, "to": 12}),
        ("window", {"from": 12, "to": 12}),
        ("negative", {"hours": 1}),
    ],
)
def test_invalid_params(rule: str, params: dict) -> None:
    with pytest.raises(vol.Invalid):
        RULES[rule].validate(params)


def test_defaults_and_schema() -> None:
    assert RULES["cheapest"].validate({}) == {
        "hours": 3,
        "after_cheapest": False,
        "second_if_alone": False,
    }
    assert RULES["window"].as_dict()["params"][1] == {
        "key": "from",
        "type": "int",
        "min": 0,
        "max": 23,
        "default": 0,
        "unit": "hour",
    }
    assert RULES["cheapest"].as_dict()["params"][2]["requires"] == "after_cheapest"


def test_parse_prices() -> None:
    attrs = {
        "price_02h": 0.1,
        "price_02h_d": 0.3,
        "price_01h": 0.05,
        "price_next_day_05h": 0.2,
        "price_03h": "n/a",
        "period": "P3",
    }
    assert parse_prices(attrs, False) == [(1, 0.05), (2, 0.2)]
    assert parse_prices(attrs, True) == [(5, 0.2)]
