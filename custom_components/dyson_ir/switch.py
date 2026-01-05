"""Switch platform for Dyson IR."""
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ACTION_TYPE_POWER,
    ACTION_TYPE_TOGGLE,
    CONF_ACTION_CODE,
    CONF_ACTION_CODE_OFF,
    CONF_ACTION_CODE_ON,
    CONF_ACTION_NAME,
    CONF_ACTION_TYPE,
    CONF_ACTIONS,
    CONF_BLASTER_ACTION,
    CONF_DEVICE_TYPE,
    DEVICE_TYPE_AC,
    DEVICE_TYPE_FAN,
    DOMAIN,
)
from .coordinator import DysonIRCoordinator
from .entity import DysonIREntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities."""
    coordinator: DysonIRCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    actions = config_entry.data.get(CONF_ACTIONS, [])

    device_type = config_entry.data.get(CONF_DEVICE_TYPE)

    entities = []
    for action in actions:
        action_type = action.get(CONF_ACTION_TYPE)

        # Determine if action is already handled by the main device entity
        handled = False
        if device_type in (DEVICE_TYPE_FAN, DEVICE_TYPE_AC, "light"):
            if action_type in (ACTION_TYPE_POWER, ACTION_TYPE_TOGGLE):
                handled = True

        if not handled and action_type in (ACTION_TYPE_POWER, ACTION_TYPE_TOGGLE):
            entities.append(DysonIRSwitch(coordinator, config_entry.entry_id, action))

    async_add_entities(entities)


class DysonIRSwitch(DysonIREntity, SwitchEntity):
    """Switch entity for Power or Toggle actions."""

    def __init__(self, coordinator: DysonIRCoordinator, entry_id: str, action: dict[str, Any]) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry_id)
        self._action = action
        self._action_name = action[CONF_ACTION_NAME]
        self._action_type = action.get(CONF_ACTION_TYPE, ACTION_TYPE_TOGGLE)

        # Override unique_id and name for this specific entity
        self._attr_name = f"{coordinator.config_entry.data.get('name')} {self._action_name}"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{self._action_name.lower().replace(' ', '_')}"
        self._attr_is_on = False  # Optimistic state

        # Load blaster config
        self._blaster_actions = coordinator.config_entry.data.get(CONF_BLASTER_ACTION, [])

    async def _send_code(self, code: str) -> None:
        """Helper to send the IR code."""
        if not self._blaster_actions or not code:
            return

        import copy

        from homeassistant.helpers import script

        actions = copy.deepcopy(self._blaster_actions)

        def inject_code(obj: Any) -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in ("command", "code", "value", "payload") and value == "IR_CODE":
                        obj[key] = [code] if key == "command" else code
                    elif isinstance(value, (dict, list)):
                        inject_code(value)
            elif isinstance(obj, list):
                for item in obj:
                    inject_code(item)

        inject_code(actions)

        for action in actions:
            # Handle Direct Service Call (New Flow) or Fallback
            if "service" in action:
                try:
                    domain, service_name = action["service"].split(".", 1)
                    target = action.get("target")
                    data = action.get("data")
                    await self.hass.services.async_call(
                        domain, service_name, service_data=data, target=target, blocking=True
                    )
                except Exception as err:
                    _LOGGER.error("Failed call %s: %s", action["service"], err)
            else:
                try:
                    script_obj = script.Script(self.hass, [action], self.name, DOMAIN)
                    await script_obj.async_run()
                except Exception as err:
                    _LOGGER.error("Failed script: %s", err)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        code = self._action.get(CONF_ACTION_CODE_ON) or self._action.get(CONF_ACTION_CODE)
        await self._send_code(code)
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        if self._action_type == ACTION_TYPE_POWER:
            code = self._action.get(CONF_ACTION_CODE_OFF)
            # If separate_codes was False or not provided, it might have fallen back to CONF_ACTION_CODE?
            # Wait, schema for power has separate_codes default=True, and optional ON/OFF/CODE.
            # If OFF code is missing (e.g. toggle mode power), use CODE?
            if not code:
                code = self._action.get(CONF_ACTION_CODE)
        else:
            # Toggle type
            code = self._action.get(CONF_ACTION_CODE)

        await self._send_code(code)
        self._attr_is_on = False
        self.async_write_ha_state()
