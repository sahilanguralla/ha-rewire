"""Config flow for Dyson IR."""
import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DEVICE_TYPES,
    DOMAIN,
    IR_CODE_HEAT_OFF,
    IR_CODE_HEAT_ON,
    IR_CODE_OSCILLATE,
    IR_CODE_POWER_OFF,
    IR_CODE_POWER_ON,
    IR_CODE_SPEED_DOWN,
    IR_CODE_SPEED_UP,
)

_LOGGER = logging.getLogger(__name__)


class DysonIRConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for Dyson IR."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Initial user step - select IR blaster device."""
        if user_input is not None:
            return await self.async_step_device()

        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))

    async def async_step_device(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Device configuration step."""
        if user_input is not None:
            self.config_data = user_input
            return await self.async_step_ir_codes()

        schema = vol.Schema(
            {
                vol.Required("name", default="Dyson Fan"): str,
                vol.Required("device_type", default="AM09"): vol.In(DEVICE_TYPES),
                vol.Required("ir_blaster_entity"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="remote")
                ),
            }
        )

        return self.async_show_form(step_id="device", data_schema=schema)

    async def async_step_ir_codes(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """IR codes configuration step."""
        if user_input is not None:
            data = {**self.config_data, "ir_codes": user_input}

            await self.async_set_unique_id(
                f"{DOMAIN}_{data['name'].lower().replace(' ', '_')}"
            )
            self._abort_if_unique_id_configured()

            return self.async_create_entry(title=data["name"], data=data)

        schema_dict = {
            vol.Required(IR_CODE_POWER_ON): str,
            vol.Required(IR_CODE_POWER_OFF): str,
            vol.Required(IR_CODE_SPEED_UP): str,
            vol.Required(IR_CODE_SPEED_DOWN): str,
            vol.Required(IR_CODE_OSCILLATE): str,
        }

        # Heat codes optional for AM09
        if self.config_data.get("device_type") == "AM09":
            schema_dict[vol.Optional(IR_CODE_HEAT_ON, default="")] = str
            schema_dict[vol.Optional(IR_CODE_HEAT_OFF, default="")] = str

        return self.async_show_form(
            step_id="ir_codes",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "info": "Paste base64-encoded IR codes from Broadlink app or "
                "Home Assistant learning"
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Get options flow."""
        return DysonIROptionsFlow(config_entry)


class DysonIROptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Dyson IR."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options_schema = vol.Schema(
            {
                vol.Optional(
                    "update_interval",
                    default=self.config_entry.options.get("update_interval", 300),
                ): int,
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)
