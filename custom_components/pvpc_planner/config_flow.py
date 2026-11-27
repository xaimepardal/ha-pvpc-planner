"""Config flow (sensor PVPC) y opciones (tamaño y publicación MQTT de las imágenes)."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
    TimeSelector,
)
import voluptuous as vol

from .const import (
    CONF_ACTIVE_FROM,
    CONF_ACTIVE_TO,
    CONF_CA_CERT,
    CONF_HEIGHT,
    CONF_INTERVAL,
    CONF_PRICE_ENTITY,
    CONF_TLS,
    CONF_TOPIC_TODAY,
    CONF_TOPIC_TOMORROW,
    CONF_WIDTH,
    DEFAULT_HEIGHT,
    DEFAULT_INTERVAL,
    DEFAULT_MQTT_PORT,
    DEFAULT_TOPIC_TODAY,
    DEFAULT_TOPIC_TOMORROW,
    DEFAULT_WIDTH,
    DOMAIN,
    MAX_SIZE,
    MIN_SIZE,
    PVPC_DOMAIN,
)
from .publisher import check_connection

_TOPICS = (CONF_TOPIC_TODAY, CONF_TOPIC_TOMORROW)
_TEXT_OPTIONS = (CONF_HOST, CONF_CA_CERT, CONF_USERNAME, *_TOPICS)
_INT_OPTIONS = (CONF_WIDTH, CONF_HEIGHT, CONF_PORT, CONF_INTERVAL)

_PIXELS = NumberSelector(
    NumberSelectorConfig(
        min=MIN_SIZE,
        max=MAX_SIZE,
        unit_of_measurement="px",
        mode=NumberSelectorMode.BOX,
    )
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_WIDTH, default=DEFAULT_WIDTH): _PIXELS,
        vol.Required(CONF_HEIGHT, default=DEFAULT_HEIGHT): _PIXELS,
        vol.Optional(CONF_HOST): TextSelector(),
        vol.Required(CONF_PORT, default=DEFAULT_MQTT_PORT): NumberSelector(
            NumberSelectorConfig(min=1, max=65535, mode=NumberSelectorMode.BOX)
        ),
        vol.Required(CONF_TLS, default=True): BooleanSelector(),
        vol.Optional(CONF_CA_CERT): TextSelector(TextSelectorConfig(multiline=True)),
        vol.Optional(CONF_USERNAME): TextSelector(
            TextSelectorConfig(autocomplete="username")
        ),
        vol.Optional(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.PASSWORD, autocomplete="current-password"
            )
        ),
        vol.Optional(CONF_TOPIC_TODAY): TextSelector(),
        vol.Optional(CONF_TOPIC_TOMORROW): TextSelector(),
        vol.Required(CONF_INTERVAL, default=DEFAULT_INTERVAL): NumberSelector(
            NumberSelectorConfig(
                min=1,
                max=1440,
                unit_of_measurement="min",
                mode=NumberSelectorMode.BOX,
            )
        ),
        vol.Optional(CONF_ACTIVE_FROM): TimeSelector(),
        vol.Optional(CONF_ACTIVE_TO): TimeSelector(),
    }
)


class PvpcPlannerConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return PvpcPlannerOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if not self.hass.config_entries.async_entries(PVPC_DOMAIN):
            return self.async_abort(reason="pvpc_missing")

        if user_input is not None:
            return self.async_create_entry(title="PVPC Planner", data=user_input)

        # Preselecciona el sensor de PVPC (la integración crea también otros).
        default = next(
            (
                e.entity_id
                for e in er.async_get(self.hass).entities.values()
                if e.platform == PVPC_DOMAIN
                and e.domain == "sensor"
                and (s := self.hass.states.get(e.entity_id))
                and "price_00h" in s.attributes
            ),
            vol.UNDEFINED,
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_PRICE_ENTITY, default=default): EntitySelector(
                    EntitySelectorConfig(integration=PVPC_DOMAIN, domain="sensor")
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)


def _options(user_input: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    """Normaliza el formulario. Contraseña vacía = la guardada, si hay usuario."""
    options = {k: v for k, v in user_input.items() if k not in _TEXT_OPTIONS}
    options |= {k: v for k in _TEXT_OPTIONS if (v := user_input.get(k, "").strip())}
    # Topic vacío = no se publica esa imagen.
    options |= {k: options.get(k, "") for k in _TOPICS}
    options |= {k: int(options[k]) for k in _INT_OPTIONS}
    if not options.get(CONF_USERNAME):
        options.pop(CONF_PASSWORD, None)
    elif not options.get(CONF_PASSWORD) and current.get(CONF_PASSWORD):
        options[CONF_PASSWORD] = current[CONF_PASSWORD]
    return options


def _valid_topic(topic: str) -> bool:
    return not set(topic) & {"+", "#", "\0"} and len(topic.encode()) <= 65535


class PvpcPlannerOptionsFlow(OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        current = dict(self.config_entry.options)
        errors: dict[str, str] = {}
        if user_input is not None:
            options = _options(user_input, current)
            if not all(_valid_topic(options[k]) for k in _TOPICS):
                errors["base"] = "invalid_topic"
            elif options.get(CONF_HOST) and (
                error := await self.hass.async_add_executor_job(
                    check_connection, options
                )
            ):
                errors["base"] = error
            if not errors:
                return self.async_create_entry(data=options)

        # La contraseña nunca se manda al navegador.
        shown = {CONF_TOPIC_TODAY: DEFAULT_TOPIC_TODAY}
        shown[CONF_TOPIC_TOMORROW] = DEFAULT_TOPIC_TOMORROW
        shown |= current | (user_input or {})
        shown.pop(CONF_PASSWORD, None)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(OPTIONS_SCHEMA, shown),
            errors=errors,
        )
