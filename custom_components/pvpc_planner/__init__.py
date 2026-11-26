"""PVPC Planner: enciende dispositivos en las horas elegidas según el PVPC."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import (
    CONF_PRICE_ENTITY,
    DOMAIN,
    PANEL_COMPONENT,
    PANEL_URL,
    STATIC_URL,
)
from .planner import Planner
from .websocket_api import async_register_commands

# Las rutas estáticas y comandos websocket no se pueden desregistrar.
_REGISTERED = f"{DOMAIN}_registered"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    planner = Planner(hass, entry.data[CONF_PRICE_ENTITY])
    await planner.async_load()
    hass.data[DOMAIN] = planner

    if not hass.data.get(_REGISTERED):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    STATIC_URL, str(Path(__file__).parent / "frontend"), False
                )
            ]
        )
        async_register_commands(hass)
        hass.data[_REGISTERED] = True

    version = (await async_get_integration(hass, DOMAIN)).version
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL,
        webcomponent_name=PANEL_COMPONENT,
        sidebar_title="PVPC Planner",
        sidebar_icon="mdi:flash",
        module_url=f"{STATIC_URL}/{PANEL_COMPONENT}.js?v={version}",
        # Un usuario no admin ya puede controlar entidades; ws_set comprueba
        # el permiso de control de cada una.
        require_admin=False,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    frontend.async_remove_panel(hass, PANEL_URL, warn_if_unknown=False)
    await hass.data.pop(DOMAIN).async_unload()
    return True
