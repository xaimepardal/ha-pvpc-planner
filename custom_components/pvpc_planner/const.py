"""Constantes de PVPC Planner."""

DOMAIN = "pvpc_planner"
PVPC_DOMAIN = "pvpc_hourly_pricing"

CONF_PRICE_ENTITY = "price_entity"

# Debe coincidir con DOMAINS en el panel.
ALLOWED_DOMAINS = frozenset({"switch", "light", "fan", "input_boolean", "humidifier"})
MAX_ENTITIES_PER_SLOT = 50
MAX_GROUPS = 50
MAX_HIDDEN = 1000
MAX_CUSTOMIZED = 1000
# Prefijo de las referencias a grupos dentro de una hora.
GROUP_PREFIX = "group:"
# El PVPC solo publica precios de hoy y mañana.
MAX_DAYS_AHEAD = 1

PANEL_URL = "pvpc-planner"
PANEL_COMPONENT = "pvpc-planner-panel"
STATIC_URL = f"/{DOMAIN}_static"

STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1

SIGNAL_UPDATED = f"{DOMAIN}_updated"
