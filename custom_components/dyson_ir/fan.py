"""Fan entity for Dyson IR."""
import logging
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ACTION_CODE,
    CONF_ACTION_NAME,
    CONF_ACTIONS,
    CONF_IR_BLASTER,
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
    """Set up fan entities."""
    coordinator: DysonIRCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities([DysonFan(coordinator, config_entry.entry_id)])


class DysonFan(DysonIREntity, FanEntity):
    """Fan entity for Dyson IR control."""

    _attr_speed_count = 3
    _attr_preset_modes = ["Off", "Low", "Medium", "High"]
    _attr_supported_features = (
        FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.OSCILLATE
    )

    def __init__(self, coordinator: DysonIRCoordinator, entry_id: str) -> None:
        """Initialize fan."""
        super().__init__(coordinator, entry_id)
        config_data = coordinator.config_entry.data
        self._attr_name = config_data.get("name", "Dyson Fan")
        self._attr_unique_id = f"{DOMAIN}_fan_{entry_id}"
        self._actions = config_data.get(CONF_ACTIONS, [])
        self._blaster_entity = config_data.get(CONF_IR_BLASTER)

    @property
    def is_on(self) -> bool:
        """Return True if fan is on."""
        return self.coordinator.data.get("power", False)

    @property
    def percentage(self) -> int | None:
        """Return speed percentage."""
        speed = self.coordinator.data.get("speed", 0)
        if speed == 0:
            return 0
        elif speed <= 33:
            return 33
        elif speed <= 66:
            return 66
        return 100

    @property
    def preset_mode(self) -> str | None:
        """Return preset mode."""
        if not self.is_on:
            return "Off"
        percent = self.percentage
        if percent == 33:
            return "Low"
        elif percent == 66:
            return "Medium"
        elif percent == 100:
            return "High"
        return None

    @property
    def oscillating(self) -> bool | None:
        """Return oscillation state."""
        return self.coordinator.data.get("oscillating", False)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on fan."""
        await self._send_action("Power On")
        self.coordinator.set_device_state({"power": True})

        if preset_mode:
            await self.async_set_preset_mode(preset_mode)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off fan."""
        await self._send_action("Power Off")
        self.coordinator.set_device_state({"power": False, "speed": 0})

    async def async_set_percentage(self, percentage: int) -> None:
        """Set fan speed by percentage."""
        if percentage == 0:
            await self.async_turn_off()
            return

        await self._set_speed_for_percentage(percentage)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode."""
        if preset_mode == "Off":
            await self.async_turn_off()
        elif preset_mode == "Low":
            await self._set_speed_for_percentage(33)
        elif preset_mode == "Medium":
            await self._set_speed_for_percentage(66)
        elif preset_mode == "High":
            await self._set_speed_for_percentage(100)

    async def async_oscillate(self, oscillating: bool) -> None:
        """Oscillate fan."""
        await self._send_action("Oscillate")
        self.coordinator.set_device_state({"oscillating": oscillating})

    async def _set_speed_for_percentage(self, percentage: int) -> None:
        """Set speed based on percentage."""
        if not self.is_on:
            await self.async_turn_on()

        # Simplified approach: send speed up or down multiple times
        current = self.percentage or 0
        target_speed = percentage

        if current < target_speed:
            # Speed up
            steps = (target_speed - current) // 33
            for _ in range(steps):
                await self._send_action("Speed Up")
        elif current > target_speed:
            # Speed down
            steps = (current - target_speed) // 33
            for _ in range(steps):
                await self._send_action("Speed Down")

        self.coordinator.set_device_state({"speed": percentage})

    async def _send_action(self, action_name: str) -> None:
        """Send IR code for a specific action name."""
        ir_code = None
        for action in self._actions:
            if action[CONF_ACTION_NAME].lower() == action_name.lower():
                ir_code = action[CONF_ACTION_CODE]
                break

        if not ir_code:
            _LOGGER.warning(f"Action '{action_name}' not configured")
            return

        try:
            # Call remote service to send IR code
            await self.hass.services.async_call(
                "remote",
                "send_command",
                {
                    "entity_id": self._blaster_entity,
                    "command": [ir_code],
                },
            )
            _LOGGER.debug(f"Sent IR code for action: {action_name}")
        except Exception as err:
            _LOGGER.error(f"Failed to send IR code for action {action_name}: {err}")
