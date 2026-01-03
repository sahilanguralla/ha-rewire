"""Config flow for Dyson IR."""
import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ACTION_CODE,
    CONF_ACTION_NAME,
    CONF_ACTIONS,
    CONF_DEVICE_TYPE,
    CONF_IR_BLASTER,
    DEVICE_TYPE_FAN,
    DEVICE_TYPES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class DysonIRConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for Dyson IR."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize config flow."""
        self.config_data: Dict[str, Any] = {}
        self.actions: list[Dict[str, str]] = []

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Step 1: Device Name and Type."""
        errors = {}
        if user_input is not None:
            self.config_data.update(user_input)
            return await self.async_step_blaster()

        schema = vol.Schema(
            {
                vol.Required("name", default="My Device"): str,
                vol.Required(CONF_DEVICE_TYPE, default=DEVICE_TYPE_FAN): vol.In(
                    DEVICE_TYPES
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_blaster(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Step 2: IR Blaster Selection."""
        if user_input is not None:
            self.config_data.update(user_input)
            return await self.async_step_actions()

        schema = vol.Schema(
            {
                vol.Required(CONF_IR_BLASTER): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="remote")
                ),
            }
        )

        return self.async_show_form(step_id="blaster", data_schema=schema)

    async def async_step_actions(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Step 3: Actions List Management."""
        errors = {}
        if user_input is not None:
            # Handle removal first
            if remove_name := user_input.get("remove_action"):
                self.actions = [
                    a for a in self.actions if a[CONF_ACTION_NAME] != remove_name
                ]
                # Return the form again to show updated list
                return await self.async_step_actions()

            if user_input.get("add_more"):
                return await self.async_step_add_action()

            if not self.actions:
                errors["base"] = "no_actions"
            else:
                self.config_data[CONF_ACTIONS] = self.actions
                return self.async_create_entry(
                    title=self.config_data["name"], data=self.config_data
                )

        # Build description with current actions
        actions_str = (
            "\n".join([f"- {a[CONF_ACTION_NAME]}" for a in self.actions])
            if self.actions
            else "No actions added yet."
        )

        schema_dict = {
            vol.Optional("add_more", default=not bool(self.actions)): bool,
        }

        if self.actions:
            schema_dict[vol.Optional("remove_action")] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {
                            "label": f"Delete {a[CONF_ACTION_NAME]}",
                            "value": a[CONF_ACTION_NAME],
                        }
                        for a in self.actions
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )

        return self.async_show_form(
            step_id="actions",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={"actions": actions_str},
            errors=errors,
        )

    async def async_step_add_action(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Sub-step to add a single action."""
        if user_input is not None:
            self.actions.append(user_input)
            return await self.async_step_actions()

        schema = vol.Schema(
            {
                vol.Required(CONF_ACTION_NAME): str,
                vol.Required(CONF_ACTION_CODE): str,
            }
        )

        return self.async_show_form(step_id="add_action", data_schema=schema)

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
