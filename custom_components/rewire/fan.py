import copy
import logging
from typing import Any, Optional

from homeassistant.components.fan import (
    FanEntity,
    FanEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import script
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
)

from .const import (
    CONF_BLASTER_ACTION,
    CONF_DEVICE_TYPE,
    CONF_MAX_SPEED,
    CONF_MIN_SPEED,
    CONF_OSCILLATE_CODE,
    CONF_POWER_OFF_CODE,
    CONF_POWER_ON_CODE,
    CONF_SPEED_DEC_CODE,
    CONF_SPEED_INC_CODE,
    CONF_SPEED_STEP,
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
    """Set up fan entity."""
    coordinator: RewireCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    device_type = config_entry.data.get(CONF_DEVICE_TYPE)

    if device_type != DEVICE_TYPE_FAN:
        return

    async_add_entities([RewireFan(coordinator, config_entry.entry_id)])


class RewireFan(RewireEntity, FanEntity):
    """Fan entity aggregating power, oscillation, and speed."""

    def __init__(
        self,
        coordinator: RewireCoordinator,
        entry_id: str,
    ) -> None:
        """Initialize the fan."""
        super().__init__(coordinator, entry_id)

        data = coordinator.config_entry.data

        self._power_on_code = data.get(CONF_POWER_ON_CODE)
        self._power_off_code = data.get(CONF_POWER_OFF_CODE)
        self._oscillate_code = data.get(CONF_OSCILLATE_CODE)
        self._speed_inc_code = data.get(CONF_SPEED_INC_CODE)
        self._speed_dec_code = data.get(CONF_SPEED_DEC_CODE)

        # Unique ID based on the entry
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_fan"
        self._attr_name = data.get("name")
        self._attr_supported_features = FanEntityFeature(0)

        if self._power_on_code and self._power_off_code:
            self._attr_supported_features |= FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF

        if self._oscillate_code:
            self._attr_supported_features |= FanEntityFeature.OSCILLATE

        if self._speed_inc_code and self._speed_dec_code:
            self._attr_supported_features |= FanEntityFeature.SET_SPEED
            self._speed_min = data.get(CONF_MIN_SPEED, 1)
            self._speed_max = data.get(CONF_MAX_SPEED, 10)
            self._speed_step = data.get(CONF_SPEED_STEP, 1)
            self._speed_range = (self._speed_min, self._speed_max)

        self._attr_is_on = False
        self._attr_oscillating = False
        self._attr_percentage = 0

        self._blaster_actions = data.get(CONF_BLASTER_ACTION, [])

    async def _send_code(self, code: str, repeats: int = 1) -> None:
        """Helper to send the IR code."""
        if not self._blaster_actions or not code:
            return

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

        for _ in range(repeats):
            for action in actions:
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

    async def async_turn_on(
        self,
        percentage: Optional[int] = None,
        preset_mode: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        if self._power_on_code:
            await self._send_code(self._power_on_code)

        self._attr_is_on = True

        if percentage is not None:
            await self.async_set_percentage(percentage)

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        if self._power_off_code:
            await self._send_code(self._power_off_code)

        self._attr_is_on = False
        self.async_write_ha_state()

    async def async_oscillate(self, oscillating: bool) -> None:
        """Oscillate the fan."""
        if self._oscillate_code:
            # Assumes toggle behavior
            await self._send_code(self._oscillate_code)
            self._attr_oscillating = oscillating
            self.async_write_ha_state()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        if percentage == 0:
            await self.async_turn_off()
            return

        if not self._speed_inc_code:
            return

        # Calculate target raw value from percentage
        target_value = percentage_to_ranged_value(self._speed_range, percentage)
        current_pct = self._attr_percentage or 0
        current_value = percentage_to_ranged_value(self._speed_range, current_pct)

        diff = target_value - current_value
        steps = int(abs(diff) / self._speed_step)

        code = self._speed_inc_code if diff > 0 else self._speed_dec_code

        if code and steps > 0:
            await self._send_code(code, repeats=steps)

        self._attr_percentage = percentage
        self.async_write_ha_state()
