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
    CONF_BLASTER_ACTION,
    CONF_DEVICE_TYPE,
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
            return await self.async_step_blaster_device()

        schema = vol.Schema(
            {
                vol.Required("name", default="My Device"): str,
                vol.Required(CONF_DEVICE_TYPE, default=DEVICE_TYPE_FAN): vol.In(
                    DEVICE_TYPES
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_blaster_device(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Step 2: Select Blaster Device."""
        if user_input is not None:
            self.config_data.update(user_input)
            return await self.async_step_blaster_action()

        schema = vol.Schema(
            {
                vol.Required("blaster_device_id"): selector.DeviceSelector(),
            }
        )

        return self.async_show_form(step_id="blaster_device", data_schema=schema)

    async def async_step_blaster_action(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Step 3: Select Blaster Action (Service)."""
        errors = {}
        if user_input is not None:
            # Construct the action dict
            service_string = user_input["service"]
            domain, service_name = service_string.split(".", 1)

            target_field = "command"  # Default
            if domain == "mqtt":
                target_field = "payload"
            elif domain in ("text", "number", "input_text", "input_number"):
                target_field = "value"

            # Action config with injected IR_CODE placeholder
            action_config = {
                "service": service_string,
                "target": {"device_id": self.config_data["blaster_device_id"]},
                "data": {target_field: "IR_CODE"},
            }
            _LOGGER.debug("Constructed blaster action config: %s", action_config)

            # Wrap in list as ActionSelector typically returns a list of actions
            self.config_data[CONF_BLASTER_ACTION] = [action_config]

            return await self.async_step_actions()

        # Get device info to find available services
        device_id = self.config_data["blaster_device_id"]

        from homeassistant.helpers import device_registry as dr

        device_registry = dr.async_get(self.hass)
        device = device_registry.async_get(device_id)
        _LOGGER.debug(
            "Looking for services for device %s (registry entry: %s)", device_id, device
        )

        options = []
        if device:
            # Get domains from config entries
            domains = set()
            for entry_id in device.config_entries:
                if entry := self.hass.config_entries.async_get_entry(entry_id):
                    domains.add(entry.domain)

            # Also generic domains that might apply
            domains.add("remote")

            # List services for these domains
            all_services = self.hass.services.async_services()
            _LOGGER.debug("Scanning domains %s for services", domains)
            for domain in domains:
                if domain_services := all_services.get(domain):
                    for service_name in domain_services:
                        full_service = f"{domain}.{service_name}"
                        options.append({"label": full_service, "value": full_service})

        if not options:
            options.append(
                {"label": "remote.send_command", "value": "remote.send_command"}
            )

        # Sort options
        options.sort(key=lambda x: x["label"])

        schema = vol.Schema(
            {
                vol.Required("service"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options, mode=selector.SelectSelectorMode.DROPDOWN
                    )
                )
            }
        )

        return self.async_show_form(
            step_id="blaster_action", data_schema=schema, errors=errors
        )

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
