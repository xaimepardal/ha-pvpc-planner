"""Cambios de horario en Europe/Madrid."""

import pytest

from .common import (
    LAVADORA,
    TERMO,
    async_move_to,
    async_setup_integration,
    is_on,
    local,
)


@pytest.mark.freeze_time("2026-10-24 23:30:00+00:00")
async def test_fall_back_repeated_hour(hass, hass_storage, freezer) -> None:
    """25/10/2026: a las 03:00 CEST vuelven a ser las 02:00 CET."""
    await async_setup_integration(
        hass,
        hass_storage,
        stored={"schedule": {"2026-10-25": {"2": [TERMO]}}, "active": []},
    )
    assert not is_on(hass, TERMO)

    await async_move_to(hass, freezer, local(2026, 10, 25, 2, fold=0))
    assert is_on(hass, TERMO)
    # La hora marcada dura dos horas reales.
    await async_move_to(hass, freezer, local(2026, 10, 25, 2, fold=1))
    assert is_on(hass, TERMO)
    await async_move_to(hass, freezer, local(2026, 10, 25, 3))
    assert not is_on(hass, TERMO)


@pytest.mark.freeze_time("2026-03-28 23:30:00+00:00")
async def test_spring_forward_missing_hour(hass, hass_storage, freezer) -> None:
    """29/03/2026: de las 02:00 CET se pasa a las 03:00 CEST."""
    await async_setup_integration(
        hass,
        hass_storage,
        stored={
            "schedule": {"2026-03-29": {"1": [LAVADORA], "2": [TERMO]}},
            "active": [],
        },
    )
    await async_move_to(hass, freezer, local(2026, 3, 29, 1))
    assert is_on(hass, LAVADORA)

    # La hora 2 no existe: TERMO nunca se enciende y LAVADORA se apaga.
    await async_move_to(hass, freezer, local(2026, 3, 29, 3))
    assert not is_on(hass, LAVADORA)
    assert not is_on(hass, TERMO)
