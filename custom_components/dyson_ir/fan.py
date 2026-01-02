"""Fan entity for Dyson IR."""
import logging
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    IR_CODE_OSCILLATE,
    IR_CODE_POWER_OFF,
    IR_CODE_POWER_ON,
    IR_CODE_SPEED_DOWN,
    IR_CODE_SPEED_UP,
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
        self._attr_name = f"Dyson {coordinator.config_entry.data.get('device_type')}"
        self._attr_unique_id = f"{DOMAIN}_fan_{entry_id}"
        self._ir_codes = coordinator.config_entry.data.get("ir_codes", {})
        self._blaster_entity = coordinator.config_entry.data.get("ir_blaster_entity")

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
        await self._send_ir_code(IR_CODE_POWER_ON)
        self.coordinator.set_device_state({"power": True})

        if preset_mode:
            await self.async_set_preset_mode(preset_mode)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off fan."""
        await self._send_ir_code(IR_CODE_POWER_OFF)
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
        await self._send_ir_code(IR_CODE_OSCILLATE)
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
                await self._send_ir_code(IR_CODE_SPEED_UP)
        elif current > target_speed:
            # Speed down
            steps = (current - target_speed) // 33
            for _ in range(steps):
                await self._send_ir_code(IR_CODE_SPEED_DOWN)

        self.coordinator.set_device_state({"speed": percentage})

    async def _send_ir_code(self, code_key: str) -> None:
        """Send IR code via blaster."""
        if code_key not in self._ir_codes:
            _LOGGER.warning(f"IR code not configured for {code_key}")
            return

        ir_code = self._ir_codes[code_key]
        if not ir_code:
            _LOGGER.warning(f"IR code is empty for {code_key}")
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
            _LOGGER.debug(f"Sent IR code for {code_key}")
        except Exception as err:
            _LOGGER.error(f"Failed to send IR code {code_key}: {err}")
