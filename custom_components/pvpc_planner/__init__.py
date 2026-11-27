"""PVPC Planner: enciende dispositivos en las horas elegidas según el PVPC."""

from __future__ import annotations

import hashlib
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_PRICE_ENTITY,
    DOMAIN,
    PANEL_COMPONENT,
    PANEL_URL,
    STATIC_URL,
)
from .planner import Planner
from .publisher import Publisher
from .websocket_api import async_register_commands

# Las rutas estáticas y comandos websocket no se pueden desregistrar.
_REGISTERED = f"{DOMAIN}_registered"
_PUBLISHER = f"{DOMAIN}_publisher"
PLATFORMS = [Platform.IMAGE]
_FRONTEND_DIR = Path(__file__).parent / "frontend"
_PANEL_JS = _FRONTEND_DIR / f"{PANEL_COMPONENT}.js"


def _panel_js_hash() -> str:
    # Cache buster: cambia con el contenido aunque no se suba la versión.
    return hashlib.sha256(_PANEL_JS.read_bytes()).hexdigest()[:12]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    planner = Planner(hass, entry.data[CONF_PRICE_ENTITY])
    await planner.async_load()
    hass.data[DOMAIN] = planner

    if not hass.data.get(_REGISTERED):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(_FRONTEND_DIR), False)]
        )
        async_register_commands(hass)
        hass.data[_REGISTERED] = True

    js_hash = await hass.async_add_executor_job(_panel_js_hash)
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL,
        webcomponent_name=PANEL_COMPONENT,
        sidebar_title="PVPC Planner",
        sidebar_icon="mdi:flash",
        module_url=f"{STATIC_URL}/{PANEL_COMPONENT}.js?v={js_hash}",
        # Un usuario no admin ya puede controlar entidades; ws_set comprueba
        # el permiso de control de cada una.
        require_admin=False,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await _async_start_publisher(hass, entry)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _async_start_publisher(hass: HomeAssistant, entry: ConfigEntry) -> None:
    old = hass.data.get(_PUBLISHER)
    hass.data[_PUBLISHER] = publisher = Publisher(
        hass, hass.data[DOMAIN], entry.options
    )
    if old:
        await old.async_stop()
    await publisher.async_start()


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    # Solo cambia la publicación MQTT: no hace falta recargar la entrada.
    await _async_start_publisher(hass, entry)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    await hass.data.pop(_PUBLISHER).async_stop()
    frontend.async_remove_panel(hass, PANEL_URL, warn_if_unknown=False)
    await hass.data.pop(DOMAIN).async_unload()
    return True
