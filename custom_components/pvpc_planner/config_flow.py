"""Config flow: elegir el sensor PVPC de la integración oficial."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .const import CONF_PRICE_ENTITY, DOMAIN, PVPC_DOMAIN


class PvpcPlannerConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

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
