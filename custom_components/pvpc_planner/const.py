"""Constantes de PVPC Planner."""

DOMAIN = "pvpc_planner"
PVPC_DOMAIN = "pvpc_hourly_pricing"

CONF_PRICE_ENTITY = "price_entity"

# Debe coincidir con DOMAINS en el panel.
ALLOWED_DOMAINS = frozenset({"switch", "light", "fan", "input_boolean", "humidifier"})
MAX_ENTITIES_PER_SLOT = 50
MAX_GROUPS = 50
MAX_TEMPLATES = 50
MAX_RULES_PER_TEMPLATE = 10
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

# Horas más baratas ($) y más caras ($$$) del día. Debe coincidir con TOP en el panel.
PRICE_LEVEL_HOURS = 6
# Iconos por dominio. Debe coincidir con DOMAIN_ICONS en el panel.
DOMAIN_ICONS = {
    "switch": "mdi:toggle-switch-variant",
    "light": "mdi:lightbulb",
    "fan": "mdi:fan",
    "input_boolean": "mdi:toggle-switch-outline",
    "humidifier": "mdi:air-humidifier",
}
GROUP_ICON = "mdi:devices"

# Publicación MQTT de las imágenes (opciones de la entrada).
CONF_TLS = "tls"
CONF_CA_CERT = "ca_cert"
CONF_TOPIC_TODAY = "topic_today"
CONF_TOPIC_TOMORROW = "topic_tomorrow"
CONF_INTERVAL = "interval"
CONF_ACTIVE_FROM = "active_from"
CONF_ACTIVE_TO = "active_to"
DEFAULT_MQTT_PORT = 8883
DEFAULT_TOPIC_TODAY = "reterminal/imagen/1"
DEFAULT_TOPIC_TOMORROW = "reterminal/imagen/2"
DEFAULT_INTERVAL = 60
