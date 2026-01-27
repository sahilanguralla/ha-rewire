"""Config flow for RewIRe."""
import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import UnitOfTemperature
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    ACTION_TYPE_BRIGHTNESS,
    ACTION_TYPE_BUTTON,
    ACTION_TYPE_INC_DEC,
    ACTION_TYPE_MODE,
    ACTION_TYPE_OSCILLATE,
    ACTION_TYPE_POWER,
    ACTION_TYPE_SPEED,
    ACTION_TYPE_TEMP,
    ACTION_TYPE_TOGGLE,
    ACTION_TYPES,
    CONF_ACTION_CODE,
    CONF_ACTION_CODE_DEC,
    CONF_ACTION_CODE_INC,
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
                vol.Required(CONF_DEVICE_TYPE, default=DEVICE_TYPE_FAN): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=DEVICE_TYPES + ["other"],
                        translation_key="device_type",
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
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
            # device_type = self.config_data.get(CONF_DEVICE_TYPE)
            # All device types now go to the generic action builder
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

    async def async_step_configure_power(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Configure Power action."""
        if user_input is not None:
            user_input[CONF_ACTION_TYPE] = ACTION_TYPE_POWER
            user_input[CONF_ACTION_NAME] = "Power"
            self.actions.append(user_input)
            return await self.async_step_actions()

        schema = vol.Schema(
            {
                vol.Required("separate_codes", default=True): bool,
                vol.Optional(CONF_POWER_ON_CODE): str,
                vol.Optional(CONF_POWER_OFF_CODE): str,
            }
        )
        return self.async_show_form(step_id="configure_power", data_schema=schema)

    async def async_step_configure_temperature(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Configure Temperature action."""
        if user_input is not None:
            user_input[CONF_ACTION_TYPE] = ACTION_TYPE_TEMP
            user_input[CONF_ACTION_NAME] = "Temperature"
            self.actions.append(user_input)
            return await self.async_step_actions()

        default_min = 16 if self.hass.config.units.temperature_unit == UnitOfTemperature.CELSIUS else 60
        default_max = 30 if self.hass.config.units.temperature_unit == UnitOfTemperature.CELSIUS else 86

        schema = vol.Schema(
            {
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
            }
        )
        return self.async_show_form(step_id="configure_temperature", data_schema=schema)

    async def async_step_configure_toggle(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Configure Toggle action."""
        if user_input is not None:
            user_input[CONF_ACTION_TYPE] = ACTION_TYPE_TOGGLE
            self.actions.append(user_input)
            return await self.async_step_actions()

        schema = vol.Schema(
            {
                vol.Required(CONF_ACTION_NAME): str,
                vol.Required(CONF_ACTION_CODE): str,
            }
        )

        return self.async_show_form(step_id="configure_toggle", data_schema=schema)

    async def async_step_configure_speed(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Configure Speed action."""
        if user_input is not None:
            user_input[CONF_ACTION_TYPE] = ACTION_TYPE_SPEED
            user_input[CONF_ACTION_NAME] = "Speed"
            self.actions.append(user_input)
            return await self.async_step_actions()

        schema = vol.Schema(
            {
                vol.Required(CONF_SPEED_INC_CODE): str,
                vol.Required(CONF_SPEED_DEC_CODE): str,
                vol.Required(CONF_MIN_SPEED, default=1): int,
                vol.Required(CONF_MAX_SPEED, default=10): int,
                vol.Required(CONF_SPEED_STEP, default=1): int,
            }
        )
        return self.async_show_form(step_id="configure_speed", data_schema=schema)

    async def async_step_configure_mode(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Configure Mode action."""
        if user_input is not None:
            # Mode handling might need to be loop-based if multiple modes are added one by one
            # But for now, let's assume one separate action entry per mode?
            # Or one action entry containing ALL modes?
            # The plan was: "Implement async_step_configure_mode (Heat/Cool/Custom + Temp Overrides)"
            # If we follow the pattern, one "Mode" action containing a list of modes?
            # Or user adds "Heat" mode action, "Cool" mode action?
            # Let's align with "Action-Based": Defining a "Mode" Capability.
            # But usually a device has "Mode" button which cycles, OR discrete codes.
            # If discrete, we need a map.
            # Let's assume discrete modes for now as separate actions?
            # "Action Name: Heat", "Code: ...". Type: Mode.
            user_input[CONF_ACTION_TYPE] = ACTION_TYPE_MODE
            self.actions.append(user_input)
            return await self.async_step_actions()

        schema = vol.Schema(
            {
                vol.Required("mode_name"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["off", "auto", "cool", "heat", "dry", "fan_only"],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        custom_value=True,
                    )
                ),
                vol.Required(CONF_ACTION_CODE): str,
            }
        )
        return self.async_show_form(step_id="configure_mode", data_schema=schema)

    async def async_step_configure_oscillate(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Configure Oscillate action."""
        if user_input is not None:
            user_input[CONF_ACTION_TYPE] = ACTION_TYPE_OSCILLATE
            self.actions.append(user_input)
            return await self.async_step_actions()

        schema = vol.Schema(
            {
                vol.Required(CONF_ACTION_NAME, default="Oscillate"): str,
                vol.Required(CONF_ACTION_CODE): str,
            }
        )
        return self.async_show_form(step_id="configure_oscillate", data_schema=schema)

    async def async_step_configure_brightness(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Configure Brightness action."""
        if user_input is not None:
            user_input[CONF_ACTION_TYPE] = ACTION_TYPE_BRIGHTNESS
            user_input[CONF_ACTION_NAME] = "Brightness"
            self.actions.append(user_input)
            return await self.async_step_actions()

        schema = vol.Schema(
            {
                vol.Required(CONF_BRIGHTNESS_INC_CODE): str,
                vol.Required(CONF_BRIGHTNESS_DEC_CODE): str,
            }
        )
        return self.async_show_form(step_id="configure_brightness", data_schema=schema)

    def _get_available_actions(self, exclude_power: bool = False) -> list[str]:
        """Get list of available actions based on device type."""
        device_type = self.config_data.get(CONF_DEVICE_TYPE)

        # Default full list
        allowed = set(ACTION_TYPES)

        if device_type == DEVICE_TYPE_AC:
            # AC: Power, Temp, Mode, Speed, Oscillate, Toggle
            allowed = {
                ACTION_TYPE_POWER,
                ACTION_TYPE_TEMP,
                ACTION_TYPE_MODE,
                ACTION_TYPE_SPEED,
                ACTION_TYPE_OSCILLATE,
                ACTION_TYPE_TOGGLE,
            }
        elif device_type == DEVICE_TYPE_FAN:
            # Fan: Power, Speed, Oscillate, Toggle
            allowed = {
                ACTION_TYPE_POWER,
                ACTION_TYPE_SPEED,
                ACTION_TYPE_OSCILLATE,
                ACTION_TYPE_TOGGLE,
            }
        elif device_type == DEVICE_TYPE_LIGHT:
            # Light: Power, Brightness, Toggle
            allowed = {
                ACTION_TYPE_POWER,
                ACTION_TYPE_BRIGHTNESS,
                ACTION_TYPE_TOGGLE,
            }
        else:  # Other
            # Other: All Actions
            allowed = set(ACTION_TYPES)

        if exclude_power and ACTION_TYPE_POWER in allowed:
            allowed.remove(ACTION_TYPE_POWER)

        # Return sorted list for UI
        return sorted(list(allowed))

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
                # Check if power action already exists
                for action in self.actions:
                    if action.get(CONF_ACTION_TYPE) == ACTION_TYPE_POWER:
                        # Filter out Power from the fallback list if it exists
                        available_actions = self._get_available_actions(exclude_power=True)
                        return self.async_show_form(
                            step_id="add_action",
                            data_schema=vol.Schema(
                                {vol.Required(CONF_ACTION_TYPE, default=ACTION_TYPE_BUTTON): vol.In(available_actions)}
                            ),
                            errors={"base": "power_action_exists"},
                        )
                return await self.async_step_configure_power()
            elif self.current_action_type == ACTION_TYPE_TEMP:
                return await self.async_step_configure_temperature()
            elif self.current_action_type == ACTION_TYPE_SPEED:
                return await self.async_step_configure_speed()
            elif self.current_action_type == ACTION_TYPE_MODE:
                return await self.async_step_configure_mode()
            elif self.current_action_type == ACTION_TYPE_OSCILLATE:
                return await self.async_step_configure_oscillate()
            elif self.current_action_type == ACTION_TYPE_BRIGHTNESS:
                return await self.async_step_configure_brightness()
            elif self.current_action_type == ACTION_TYPE_TOGGLE:
                return await self.async_step_configure_toggle()

            return await self.async_step_configure_action()

        available_actions = self._get_available_actions()
        schema = vol.Schema(
            {
                vol.Required(CONF_ACTION_TYPE, default=available_actions[0]): vol.In(available_actions),
            }
        )

        return self.async_show_form(step_id="add_action", data_schema=schema)

    async def async_step_configure_action(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Configure Generic details (Button, Inc/Dec)."""
        if user_input is not None:
            user_input[CONF_ACTION_TYPE] = self.current_action_type
            self.actions.append(user_input)
            return await self.async_step_actions()

        data_schema = {vol.Required(CONF_ACTION_NAME): str}

        if self.current_action_type == ACTION_TYPE_INC_DEC:
            data_schema.update(
                {
                    vol.Required(CONF_MIN_VALUE, default=10): int,
                    vol.Required(CONF_MAX_VALUE, default=30): int,
                    vol.Required(CONF_STEP_VALUE, default=1): int,
                    vol.Required(CONF_ACTION_CODE_INC): str,
                    vol.Required(CONF_ACTION_CODE_DEC): str,
                }
            )
        else:  # Button and fallback
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
