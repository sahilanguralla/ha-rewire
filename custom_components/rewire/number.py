import copy
import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import script
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    ACTION_TYPE_INC_DEC,
    CONF_ACTION_CODE_DEC,
    CONF_ACTION_CODE_INC,
    CONF_ACTION_NAME,
    CONF_ACTION_TYPE,
    CONF_ACTIONS,
    CONF_BLASTER_ACTION,
    CONF_DEVICE_TYPE,
    CONF_MAX_VALUE,
    CONF_MIN_VALUE,
    CONF_STEP_VALUE,
    DEVICE_TYPE_AC,
    DEVICE_TYPE_FAN,
    DOMAIN,
)
from .coordinator import RewireCoordinator
from .entity import RewireEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entity."""
    coordinator: RewireCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    actions = config_entry.data.get(CONF_ACTIONS, [])

    device_type = config_entry.data.get(CONF_DEVICE_TYPE)

    entities = []
    for action in actions:
        if action.get(CONF_ACTION_TYPE) == ACTION_TYPE_INC_DEC:
            name = action.get(CONF_ACTION_NAME, "").lower()
            handled = False

            if device_type == DEVICE_TYPE_FAN and "speed" in name:
                handled = True
            elif device_type == DEVICE_TYPE_AC and ("temp" in name or "climate" in name):
                handled = True
            elif device_type == "light" and "brightness" in name:
                handled = True

            if not handled:
                entities.append(RewireNumber(coordinator, config_entry.entry_id, action))

    async_add_entities(entities)


class RewireNumber(RewireEntity, NumberEntity, RestoreEntity):
    """Number representation of inc/dec buttons."""

    def __init__(self, coordinator: RewireCoordinator, entry_id: str, action: dict[str, Any]) -> None:
        """Initialize the number."""
        super().__init__(coordinator, entry_id)
        self._action = action
        self._action_name = action[CONF_ACTION_NAME]

        # Override unique_id and name
        self._attr_name = f"{coordinator.config_entry.data.get('name')} {self._action_name}"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{self._action_name.lower().replace(' ', '_')}"

        # Configuration
        self._attr_native_min_value = float(action.get(CONF_MIN_VALUE, 10))
        self._attr_native_max_value = float(action.get(CONF_MAX_VALUE, 30))
        self._attr_native_step = float(action.get(CONF_STEP_VALUE, 1))
        self._attr_mode = NumberMode.SLIDER

        # Default starting value (middle of range)
        self._attr_native_value = (self._attr_native_min_value + self._attr_native_max_value) / 2

        # Load blaster config
        self._blaster_actions = coordinator.config_entry.data.get(CONF_BLASTER_ACTION, [])

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                self._attr_native_value = float(last_state.state)
            except ValueError:
                pass

    async def _send_code(self, code: str, repeats: int = 1) -> None:
        """Helper to send the IR code."""
        if not self._blaster_actions or not code:
            return

        base_actions = copy.deepcopy(self._blaster_actions)

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

        inject_code(base_actions)

        # Execute 'repeats' times
        for _ in range(repeats):
            for action in base_actions:
                # Handle Direct Service Call or Fallback
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

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        if value == self._attr_native_value:
            return

        diff = value - self._attr_native_value
        steps = int(abs(diff) / self._attr_native_step)

        code = self._action.get(CONF_ACTION_CODE_INC) if diff > 0 else self._action.get(CONF_ACTION_CODE_DEC)

        if code and steps > 0:
            await self._send_code(code, repeats=steps)

        self._attr_native_value = value
        self.async_write_ha_state()
