"""Constantes de PVPC Planner."""

DOMAIN = "pvpc_planner"
PVPC_DOMAIN = "pvpc_hourly_pricing"

CONF_PRICE_ENTITY = "price_entity"

# Debe coincidir con DOMAINS del panel.
SUPPORTED_DOMAINS = frozenset({"fan", "humidifier", "input_boolean", "light", "switch"})

PANEL_URL = "pvpc-planner"
PANEL_COMPONENT = "pvpc-planner-panel"
STATIC_URL = f"/{DOMAIN}_static"

STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1

SIGNAL_UPDATED = f"{DOMAIN}_updated"
