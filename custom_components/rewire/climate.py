import asyncio
import copy
import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import script
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ACTION_TYPE_OSCILLATE,
    ACTION_TYPE_POWER,
    ACTION_TYPE_SPEED,
    ACTION_TYPE_TEMP,
    CONF_ACTION_TYPE,
    CONF_ACTIONS,
    CONF_BLASTER_ACTION,
    CONF_DEVICE_TYPE,
    CONF_MAX_SPEED,
    CONF_MAX_TEMP,
    CONF_MIN_SPEED,
    CONF_MIN_TEMP,
    CONF_POWER_OFF_CODE,
    CONF_POWER_ON_CODE,
    CONF_SPEED_DEC_CODE,
    CONF_SPEED_INC_CODE,
    CONF_SPEED_STEP,
    CONF_TEMP_DEC_CODE,
    CONF_TEMP_INC_CODE,
    CONF_TEMP_STEP,
    CONF_TEMP_UNIT,
    DEVICE_TYPE_AC,
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
    """Set up climate entity."""
    coordinator: RewireCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    device_type = config_entry.data.get(CONF_DEVICE_TYPE)

    if device_type != DEVICE_TYPE_AC:
        return

    async_add_entities([RewireClimate(coordinator, config_entry.entry_id)])


class RewireClimate(RewireEntity, ClimateEntity):
    """Climate entity aggregating power (hvac_mode) and temperature."""

    def __init__(
        self,
        coordinator: RewireCoordinator,
        entry_id: str,
    ) -> None:
        """Initialize the climate."""
        super().__init__(coordinator, entry_id)

        data = coordinator.config_entry.data

        self._base_features = ClimateEntityFeature(0)
        self._actions = data.get(CONF_ACTIONS, [])

        # Initialize defaults
        self._power_on_code = None
        self._power_off_code = None
        self._temp_inc_code = None
        self._temp_dec_code = None
        self._oscillate_code = None
        self._speed_inc_code = None
        self._speed_dec_code = None
        self._temp_unit = None  # Store configured temperature unit
        self._mode_features = {}
        self._toggle_modes_order = []
        self._toggle_code = None
        min_temp = 16
        max_temp = 30
        temp_step = 1
        min_speed = 1
        max_speed = 10
        speed_step = 1

        self._hvac_mode_codes = {}

        if self._actions:
            # New Action-Based Config
            for action in self._actions:
                atype = action.get(CONF_ACTION_TYPE)
                if atype == ACTION_TYPE_POWER:
                    self._power_on_code = action.get(CONF_POWER_ON_CODE)
                    self._power_off_code = action.get(CONF_POWER_OFF_CODE)
                elif atype == ACTION_TYPE_TEMP:
                    self._temp_inc_code = action.get(CONF_TEMP_INC_CODE)
                    self._temp_dec_code = action.get(CONF_TEMP_DEC_CODE)
                    min_temp = action.get(CONF_MIN_TEMP, min_temp)
                    max_temp = action.get(CONF_MAX_TEMP, max_temp)
                    temp_step = action.get(CONF_TEMP_STEP, temp_step)
                    # Read configured temperature unit
                    temp_unit_str = action.get(CONF_TEMP_UNIT, "celsius")
                    self._temp_unit = (
                        UnitOfTemperature.CELSIUS if temp_unit_str == "celsius" else UnitOfTemperature.FAHRENHEIT
                    )
                elif atype == ACTION_TYPE_OSCILLATE:
                    self._oscillate_code = action.get("ir_code")
                elif atype == ACTION_TYPE_SPEED:
                    self._speed_inc_code = action.get(CONF_SPEED_INC_CODE)
                    self._speed_dec_code = action.get(CONF_SPEED_DEC_CODE)
                    min_speed = action.get(CONF_MIN_SPEED, min_speed)
                    max_speed = action.get(CONF_MAX_SPEED, max_speed)
                    speed_step = action.get(CONF_SPEED_STEP, speed_step)
                    mode_name = action.get("mode_name")
                    ir_code = action.get("ir_code")
                    if mode_name:
                        if ir_code:
                            self._hvac_mode_codes[mode_name] = ir_code
                        self._mode_features[mode_name] = {
                            "speed": action.get("supports_speed", True),
                            "temp": action.get("supports_temp", True),
                        }
                        if action.get("is_toggle"):
                            if ir_code and not getattr(self, "_toggle_code", None):
                                self._toggle_code = ir_code
                            self._toggle_modes_order.append(mode_name)
        else:
            # Legacy Linear Config
            self._power_on_code = data.get(CONF_POWER_ON_CODE)
            self._power_off_code = data.get(CONF_POWER_OFF_CODE)
            self._temp_inc_code = data.get(CONF_TEMP_INC_CODE)
            self._temp_dec_code = data.get(CONF_TEMP_DEC_CODE)
            self._speed_inc_code = data.get(CONF_SPEED_INC_CODE)
            self._speed_dec_code = data.get(CONF_SPEED_DEC_CODE)
            min_temp = data.get(CONF_MIN_TEMP, 16)
            max_temp = data.get(CONF_MAX_TEMP, 30)
            temp_step = data.get(CONF_TEMP_STEP, 1)
            min_speed = data.get(CONF_MIN_SPEED, 1)
            max_speed = data.get(CONF_MAX_SPEED, 10)
            speed_step = data.get(CONF_SPEED_STEP, 1)

        self._attr_unique_id = f"{DOMAIN}_{entry_id}_climate"
        self._attr_name = data.get("name")
        self._attr_supported_features = ClimateEntityFeature(0)
        self._attr_hvac_modes = []

        # Default modes logic
        # If discrete modes are configured, use them.
        # Otherwise fallback to Power-based defaults.
        valid_modes = [HVACMode.OFF]
        if self._hvac_mode_codes:
            for mode in self._hvac_mode_codes:
                if mode in [HVACMode.COOL, HVACMode.HEAT, HVACMode.AUTO, HVACMode.DRY, HVACMode.FAN_ONLY]:
                    valid_modes.append(mode)

        self._attr_hvac_modes = sorted(list(set(valid_modes)))

        if self._power_on_code or self._power_off_code or len(self._attr_hvac_modes) > 1:
            self._base_features |= ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF

        if self._temp_inc_code and self._temp_dec_code:
            self._base_features |= ClimateEntityFeature.TARGET_TEMPERATURE

            system_unit = coordinator.hass.config.units.temperature_unit
            self._attr_temperature_unit = system_unit

            if self._temp_unit and self._temp_unit != system_unit:
                from homeassistant.util.unit_conversion import TemperatureConverter

                self._attr_min_temp = round(TemperatureConverter.convert(min_temp, self._temp_unit, system_unit), 2)
                self._attr_max_temp = round(TemperatureConverter.convert(max_temp, self._temp_unit, system_unit), 2)

                if self._temp_unit == UnitOfTemperature.FAHRENHEIT and system_unit == UnitOfTemperature.CELSIUS:
                    self._attr_target_temperature_step = round(temp_step * 5 / 9, 2)
                elif self._temp_unit == UnitOfTemperature.CELSIUS and system_unit == UnitOfTemperature.FAHRENHEIT:
                    self._attr_target_temperature_step = round(temp_step * 9 / 5, 2)
                else:
                    self._attr_target_temperature_step = float(temp_step)
            else:
                self._attr_min_temp = float(min_temp)
                self._attr_max_temp = float(max_temp)
                self._attr_target_temperature_step = float(temp_step)

            self._attr_target_temperature = self._attr_min_temp
        else:
            self._attr_temperature_unit = coordinator.hass.config.units.temperature_unit

        if self._oscillate_code:
            self._base_features |= ClimateEntityFeature.SWING_MODE
            self._attr_swing_modes = ["off", "on"]
            self._attr_swing_mode = "off"

        self._attr_hvac_mode = HVACMode.OFF

        # Fan Mode Setup
        if self._speed_inc_code and self._speed_dec_code:
            self._base_features |= ClimateEntityFeature.FAN_MODE
            # Generate numeric string modes "1", "2", ...
            # Or use steps.
            steps = int((max_speed - min_speed) / speed_step) + 1
            self._attr_fan_modes = [str(i) for i in range(1, steps + 1)]
            self._attr_fan_mode = self._attr_fan_modes[0]
            self._fan_speed_min = min_speed
            self._fan_speed_step = speed_step
            self._curr_speed_idx = 0

        self._blaster_actions = data.get(CONF_BLASTER_ACTION, [])

        # Apply initial state if configured
        initial_state = data.get("initial_state", {})
        if initial_state:
            if "current_hvac_mode" in initial_state:
                mode_str = initial_state["current_hvac_mode"]
                # Map string to HVACMode
                mode_map = {
                    "off": HVACMode.OFF,
                    "cool": HVACMode.COOL,
                    "heat": HVACMode.HEAT,
                    "auto": HVACMode.AUTO,
                    "dry": HVACMode.DRY,
                    "fan_only": HVACMode.FAN_ONLY,
                }
                self._attr_hvac_mode = mode_map.get(mode_str, HVACMode.OFF)

            if "power_state" in initial_state and not initial_state["power_state"]:
                self._attr_hvac_mode = HVACMode.OFF

            if "current_temp" in initial_state:
                configured_temp = float(initial_state["current_temp"])
                system_unit = coordinator.hass.config.units.temperature_unit
                if self._temp_unit and self._temp_unit != system_unit:
                    from homeassistant.util.unit_conversion import TemperatureConverter

                    self._attr_target_temperature = round(
                        TemperatureConverter.convert(configured_temp, self._temp_unit, system_unit), 2
                    )
                else:
                    self._attr_target_temperature = configured_temp

            if "current_speed" in initial_state:
                speed_val = initial_state["current_speed"]
                if hasattr(self, "_attr_fan_modes"):
                    idx = int((speed_val - min_speed) / speed_step)
                    if 0 <= idx < len(self._attr_fan_modes):
                        self._attr_fan_mode = self._attr_fan_modes[idx]
                        self._curr_speed_idx = idx

            # Fallback for old configs
            if "current_fan_mode" in initial_state:
                self._attr_fan_mode = initial_state["current_fan_mode"]
                # Update internal index
                if hasattr(self, "_attr_fan_modes") and initial_state["current_fan_mode"] in self._attr_fan_modes:
                    self._curr_speed_idx = self._attr_fan_modes.index(initial_state["current_fan_mode"])

            if "oscillating" in initial_state:
                self._attr_swing_mode = "on" if initial_state["oscillating"] else "off"

    async def _send_code(self, code: str, repeats: int = 1, delay: float = 0.0) -> None:
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

        for i in range(repeats):
            # Apply delay if requested and not the first iteration
            if delay > 0 and i > 0:
                await asyncio.sleep(delay)

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

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        if hvac_mode == HVACMode.OFF:
            if self._power_off_code:
                await self._send_code(self._power_off_code)
            self._attr_hvac_mode = HVACMode.OFF
            self.coordinator.set_device_state({"power": False})
        else:
            # Check if we have a specific code for this mode
            code_sent = False

            # If target mode is a toggle mode and we have a current toggle state
            current_mode = self._attr_hvac_mode
            if (
                hvac_mode in self._toggle_modes_order
                and getattr(self, "_toggle_code", None)
                and current_mode in self._toggle_modes_order
            ):
                current_idx = self._toggle_modes_order.index(current_mode)
                target_idx = self._toggle_modes_order.index(hvac_mode)

                # Calculate number of presses needed
                diff = (target_idx - current_idx) % len(self._toggle_modes_order)
                if diff > 0:
                    await self._send_code(self._toggle_code, repeats=diff, delay=0.5)
                    code_sent = True

            # Send explicit mode code if it wasn't a toggle jump
            if not code_sent and self._hvac_mode_codes and hvac_mode in self._hvac_mode_codes:
                await self._send_code(self._hvac_mode_codes[hvac_mode])
                code_sent = True

            # If no specific mode code sent, or if allow Power ON fallback
            # (Logic: If we have modes, we sent the mode code. Does that turn it on? Usually yes.)
            # If we DON'T have discrete modes (just toggle), we send Power On.
            if (
                not code_sent
                and not self._hvac_mode_codes
                and self._attr_hvac_mode == HVACMode.OFF
                and self._power_on_code
            ):
                # Legacy toggle behavior
                await self._send_code(self._power_on_code)

            self._attr_hvac_mode = hvac_mode
            self.coordinator.set_device_state({"power": True})

        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        if self._attr_hvac_mode == HVACMode.OFF:
            _LOGGER.debug("Fan mode control ignored because AC is OFF")
            self.async_write_ha_state()
            return

        if not self._speed_inc_code:
            return

        if fan_mode not in self._attr_fan_modes:
            return

        target_idx = self._attr_fan_modes.index(fan_mode)
        diff = target_idx - self._curr_speed_idx

        if diff == 0:
            return

        direction = 1 if diff > 0 else -1
        code = self._speed_inc_code if direction > 0 else self._speed_dec_code

        if code:
            # Just one step at a time for reliability, user can slide/select again
            await self._send_code(code, repeats=1)
            # Update internal index
            self._curr_speed_idx += direction
            self._attr_fan_mode = self._attr_fan_modes[self._curr_speed_idx]

        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        if self._power_on_code:
            await self._send_code(self._power_on_code)
        modes = [m for m in self._attr_hvac_modes if m != HVACMode.OFF]
        if modes:
            self._attr_hvac_mode = modes[0]
        else:
            self._attr_hvac_mode = HVACMode.COOL
        self.coordinator.set_device_state({"power": True})
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        await self.async_set_hvac_mode(HVACMode.OFF)

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return the list of supported features."""
        features = self._base_features
        if self._attr_hvac_mode == HVACMode.OFF:
            features &= ~ClimateEntityFeature.TARGET_TEMPERATURE
            features &= ~ClimateEntityFeature.FAN_MODE
            features &= ~ClimateEntityFeature.SWING_MODE
        else:
            # Dynamically restrict speed/temp based on the current mode config
            mode_config = self._mode_features.get(self._attr_hvac_mode, {})
            supports_temp = mode_config.get("temp", True)
            supports_speed = mode_config.get("speed", True)

            if not supports_temp:
                features &= ~ClimateEntityFeature.TARGET_TEMPERATURE
            if not supports_speed:
                features &= ~ClimateEntityFeature.FAN_MODE

        return features

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if self._attr_hvac_mode == HVACMode.OFF:
            _LOGGER.debug("Temperature control ignored because AC is OFF")
            self.async_write_ha_state()
            return

        temperature = kwargs.get("temperature")
        if temperature is None or not self._temp_inc_code:
            return

        diff = temperature - self._attr_target_temperature
        if abs(diff) < 0.01:
            return

        # Restrict to increasing/decreasing by only one step at a time
        direction = 1 if diff > 0 else -1
        code = self._temp_inc_code if direction > 0 else self._temp_dec_code

        if code:
            await self._send_code(code, repeats=1)

        self._attr_target_temperature += direction * self._attr_target_temperature_step
        self._attr_target_temperature = round(self._attr_target_temperature, 2)
        self.async_write_ha_state()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set new target swing operation."""
        if not self._oscillate_code:
            return

        if self._attr_hvac_mode == HVACMode.OFF:
            _LOGGER.debug("Swing mode ignored because AC is OFF")
            return

        # Assuming single code toggles oscillation
        # In a real scenario, might need ON/OFF codes.
        # But for now, user provides "Oscillate Code" which usually toggles.
        # If we want exact state, we assume the user syncs it.
        # Or we send the code.
        await self._send_code(self._oscillate_code)

        self._attr_swing_mode = swing_mode
        self.async_write_ha_state()
