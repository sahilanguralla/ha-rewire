"""Config flow for RewIRe."""
import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import UnitOfTemperature
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    ACTION_TYPE_BUTTON,
    ACTION_TYPE_INC_DEC,
    ACTION_TYPE_POWER,
    ACTION_TYPE_TOGGLE,
    ACTION_TYPES,
    CONF_ACTION_CODE,
    CONF_ACTION_CODE_DEC,
    CONF_ACTION_CODE_INC,
    CONF_ACTION_CODE_OFF,
    CONF_ACTION_CODE_ON,
    CONF_ACTION_NAME,
    CONF_ACTION_TYPE,
    CONF_ACTIONS,
    CONF_BLASTER_ACTION,
    CONF_BRIGHTNESS_DEC_CODE,
    CONF_BRIGHTNESS_INC_CODE,
    CONF_DEVICE_TYPE,
    CONF_MAX_SPEED,
    CONF_MAX_TEMP,
    CONF_MAX_VALUE,
    CONF_MIN_SPEED,
    CONF_MIN_TEMP,
    CONF_MIN_VALUE,
    CONF_OSCILLATE_CODE,
    CONF_POWER_OFF_CODE,
    CONF_POWER_ON_CODE,
    CONF_SPEED_DEC_CODE,
    CONF_SPEED_INC_CODE,
    CONF_SPEED_STEP,
    CONF_STEP_VALUE,
    CONF_TEMP_DEC_CODE,
    CONF_TEMP_INC_CODE,
    CONF_TEMP_STEP,
    DEVICE_TYPE_AC,
    DEVICE_TYPE_FAN,
    DEVICE_TYPE_LIGHT,
    DEVICE_TYPES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class RewireConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for RewIRe."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize config flow."""
        self.config_data: Dict[str, Any] = {}
        self.actions: list[Dict[str, Any]] = []
        self.current_action_type: Optional[str] = None

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Step 1: Device Name and Type."""
        errors = {}
        if user_input is not None:
            self.config_data.update(user_input)
            return await self.async_step_blaster_device()

        schema = vol.Schema(
            {
                vol.Required("name", default="My Device"): str,
                vol.Required(CONF_DEVICE_TYPE, default=DEVICE_TYPE_FAN): vol.In(DEVICE_TYPES + ["other"]),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_blaster_device(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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

    async def async_step_blaster_action(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Step 3: Select Blaster Entity/Action."""
        errors = {}
        if user_input is not None:
            # ... (Action config construction similar to before) ...
            selection = user_input["selection"]
            if selection.startswith("text.") or selection.startswith("input_text."):
                entity_id = selection
                domain = entity_id.split(".", 1)[0]
                service = f"{domain}.set_value"
                action_config = {
                    "service": service,
                    "target": {"entity_id": entity_id},
                    "data": {"value": "IR_CODE"},
                }
            else:
                service_string = selection
                domain = service_string.split(".", 1)[0]
                target_field = "command"
                if domain == "mqtt":
                    target_field = "payload"
                action_config = {
                    "service": service_string,
                    "target": {"device_id": self.config_data["blaster_device_id"]},
                    "data": {target_field: "IR_CODE"},
                }

            self.config_data[CONF_BLASTER_ACTION] = [action_config]

            # Route based on device type
            device_type = self.config_data.get(CONF_DEVICE_TYPE)
            if device_type == DEVICE_TYPE_FAN:
                return await self.async_step_configure_fan()
            elif device_type == DEVICE_TYPE_AC:
                return await self.async_step_configure_climate()
            elif device_type == DEVICE_TYPE_LIGHT:  # Assuming you added this constant
                return await self.async_step_configure_light()
            elif device_type == "light":  # Fallback if constant missing
                return await self.async_step_configure_light()
            else:
                return await self.async_step_actions()

        # ... (Device discovery logic same as before) ...
        device_id = self.config_data["blaster_device_id"]
        from homeassistant.helpers import entity_registry as er

        entity_registry = er.async_get(self.hass)
        device_entities = er.async_entries_for_device(entity_registry, device_id)
        options = []
        text_entities = [e for e in device_entities if e.domain in ("text", "input_text")]
        for e in text_entities:
            label = f"{e.original_name or e.name or e.entity_id} ({e.entity_id})"
            options.append({"label": label, "value": e.entity_id})

        if not options:
            domains = set(e.domain for e in device_entities)
            domains.add("remote")
            all_services = self.hass.services.async_services()
            for domain in domains:
                if domain_services := all_services.get(domain):
                    for service_name in domain_services:
                        full_service = f"{domain}.{service_name}"
                        options.append({"label": full_service, "value": full_service})

        if not options:
            options.append({"label": "remote.send_command", "value": "remote.send_command"})

        options.sort(key=lambda x: x["label"])

        schema = vol.Schema(
            {
                vol.Required("selection"): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=options, mode=selector.SelectSelectorMode.DROPDOWN)
                )
            }
        )

        return self.async_show_form(step_id="blaster_action", data_schema=schema, errors=errors)

    async def async_step_configure_fan(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Configure Fan specific codes."""
        if user_input is not None:
            self.config_data.update(user_input)
            return self.async_create_entry(title=self.config_data["name"], data=self.config_data)

        schema = vol.Schema(
            {
                vol.Required(CONF_POWER_ON_CODE): str,
                vol.Required(CONF_POWER_OFF_CODE): str,
                vol.Optional(CONF_OSCILLATE_CODE): str,
                vol.Optional(CONF_SPEED_INC_CODE): str,
                vol.Optional(CONF_SPEED_DEC_CODE): str,
                vol.Required(CONF_MIN_SPEED, default=1): int,
                vol.Required(CONF_MAX_SPEED, default=10): int,
                vol.Required(CONF_SPEED_STEP, default=1): int,
            }
        )
        return self.async_show_form(step_id="configure_fan", data_schema=schema)

    async def async_step_configure_climate(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Configure Climate specific codes."""
        if user_input is not None:
            self.config_data.update(user_input)
            return self.async_create_entry(title=self.config_data["name"], data=self.config_data)

        default_min = 16 if self.hass.config.units.temperature_unit == UnitOfTemperature.CELSIUS else 60
        default_max = 30 if self.hass.config.units.temperature_unit == UnitOfTemperature.CELSIUS else 86

        schema = vol.Schema(
            {
                vol.Required(CONF_POWER_ON_CODE): str,
                vol.Required(CONF_POWER_OFF_CODE): str,
                vol.Required(CONF_TEMP_INC_CODE): str,
                vol.Required(CONF_TEMP_DEC_CODE): str,
                vol.Required(CONF_MIN_TEMP, default=default_min): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement=self.hass.config.units.temperature_unit,
                        step=1,
                    )
                ),
                vol.Required(CONF_MAX_TEMP, default=default_max): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement=self.hass.config.units.temperature_unit,
                        step=1,
                    )
                ),
                vol.Required(CONF_TEMP_STEP, default=1): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        mode=selector.NumberSelectorMode.BOX,
                        min=0.1,
                        max=5.0,
                        step=0.1,
                    )
                ),
                vol.Optional(CONF_SPEED_INC_CODE): str,
                vol.Optional(CONF_SPEED_DEC_CODE): str,
                vol.Required(CONF_MIN_SPEED, default=1): int,
                vol.Required(CONF_MAX_SPEED, default=10): int,
                vol.Required(CONF_SPEED_STEP, default=1): int,
            }
        )
        return self.async_show_form(step_id="configure_climate", data_schema=schema)

    async def async_step_configure_light(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Configure Light specific codes."""
        if user_input is not None:
            self.config_data.update(user_input)
            return self.async_create_entry(title=self.config_data["name"], data=self.config_data)

        schema = vol.Schema(
            {
                vol.Required(CONF_POWER_ON_CODE): str,
                vol.Required(CONF_POWER_OFF_CODE): str,
                vol.Optional(CONF_BRIGHTNESS_INC_CODE): str,
                vol.Optional(CONF_BRIGHTNESS_DEC_CODE): str,
            }
        )
        return self.async_show_form(step_id="configure_light", data_schema=schema)

    # Legacy / Other Actions Steps
    async def async_step_actions(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Step 3: Actions List Management."""
        errors = {}
        if user_input is not None:
            if remove_name := user_input.get("remove_action"):
                self.actions = [a for a in self.actions if a[CONF_ACTION_NAME] != remove_name]
                return await self.async_step_actions()

            if user_input.get("add_more"):
                return await self.async_step_add_action()

            if not self.actions:
                errors["base"] = "no_actions"
            else:
                self.config_data[CONF_ACTIONS] = self.actions
                return self.async_create_entry(title=self.config_data["name"], data=self.config_data)

        actions_str = (
            "\n".join([f"- {a[CONF_ACTION_NAME]}" for a in self.actions]) if self.actions else "No actions added yet."
        )

        schema_dict = {
            vol.Optional("add_more", default=not bool(self.actions)): bool,
        }

        if self.actions:
            schema_dict[vol.Optional("remove_action")] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"label": f"Delete {a[CONF_ACTION_NAME]}", "value": a[CONF_ACTION_NAME]} for a in self.actions
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

    async def async_step_add_action(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Sub-step to add a single action: Select Type."""
        if user_input is not None:
            self.current_action_type = user_input[CONF_ACTION_TYPE]
            if self.current_action_type == ACTION_TYPE_POWER:
                for action in self.actions:
                    if action.get(CONF_ACTION_TYPE) == ACTION_TYPE_POWER:
                        return self.async_show_form(
                            step_id="add_action",
                            data_schema=vol.Schema(
                                {
                                    vol.Required(CONF_ACTION_TYPE, default=ACTION_TYPE_BUTTON): vol.In(
                                        [t for t in ACTION_TYPES if t != ACTION_TYPE_POWER]
                                    )
                                }
                            ),
                            errors={"base": "power_action_exists"},
                        )
            return await self.async_step_configure_action()

        schema = vol.Schema(
            {
                vol.Required(CONF_ACTION_TYPE, default=ACTION_TYPE_BUTTON): vol.In(ACTION_TYPES),
            }
        )

        return self.async_show_form(step_id="add_action", data_schema=schema)

    async def async_step_configure_action(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Configure the details for the selected action type."""
        if user_input is not None:
            user_input[CONF_ACTION_TYPE] = self.current_action_type
            self.actions.append(user_input)
            return await self.async_step_actions()

        data_schema = {vol.Required(CONF_ACTION_NAME): str}

        if self.current_action_type == ACTION_TYPE_POWER:
            data_schema.update(
                {
                    vol.Required("separate_codes", default=True): bool,
                    vol.Optional(CONF_ACTION_CODE_ON): str,
                    vol.Optional(CONF_ACTION_CODE_OFF): str,
                    vol.Optional(CONF_ACTION_CODE): str,
                }
            )
        elif self.current_action_type == ACTION_TYPE_TOGGLE:
            data_schema.update({vol.Required(CONF_ACTION_CODE): str})
        elif self.current_action_type == ACTION_TYPE_INC_DEC:
            data_schema.update(
                {
                    vol.Required(CONF_MIN_VALUE, default=10): int,
                    vol.Required(CONF_MAX_VALUE, default=30): int,
                    vol.Required(CONF_STEP_VALUE, default=1): int,
                    vol.Required(CONF_ACTION_CODE_INC): str,
                    vol.Required(CONF_ACTION_CODE_DEC): str,
                }
            )
        elif self.current_action_type == ACTION_TYPE_BUTTON:
            data_schema.update({vol.Required(CONF_ACTION_CODE): str})

        return self.async_show_form(
            step_id="configure_action",
            data_schema=vol.Schema(data_schema),
            description_placeholders={"type": self.current_action_type},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Get options flow."""
        return RewireOptionsFlow()


class RewireOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for RewIRe."""

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
