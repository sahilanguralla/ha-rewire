"""Climate platform for Dyson IR."""
import asyncio
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
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_BLASTER_ACTION,
    CONF_DEVICE_TYPE,
    CONF_POWER_OFF_CODE,
    CONF_POWER_ON_CODE,
    CONF_TEMP_DEC_CODE,
    CONF_TEMP_INC_CODE,
    DEVICE_TYPE_AC,
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
    """Set up climate entity."""
    coordinator: DysonIRCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    device_type = config_entry.data.get(CONF_DEVICE_TYPE)

    if device_type != DEVICE_TYPE_AC:
        return

    async_add_entities([DysonIRClimate(coordinator, config_entry.entry_id)])


class DysonIRClimate(DysonIREntity, ClimateEntity):
    """Climate entity aggregating power (hvac_mode) and temperature."""

    def __init__(
        self,
        coordinator: DysonIRCoordinator,
        entry_id: str,
    ) -> None:
        """Initialize the climate."""
        super().__init__(coordinator, entry_id)

        data = coordinator.config_entry.data

        self._power_on_code = data.get(CONF_POWER_ON_CODE)
        self._power_off_code = data.get(CONF_POWER_OFF_CODE)
        self._temp_inc_code = data.get(CONF_TEMP_INC_CODE)
        self._temp_dec_code = data.get(CONF_TEMP_DEC_CODE)

        self._attr_unique_id = f"{DOMAIN}_{entry_id}_climate"
        self._attr_name = data.get("name")
        self._attr_supported_features = ClimateEntityFeature(0)
        self._attr_hvac_modes = []

        if self._power_on_code and self._power_off_code:
            self._attr_supported_features |= ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
            self._attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT]

        if self._temp_inc_code and self._temp_dec_code:
            self._attr_supported_features |= ClimateEntityFeature.TARGET_TEMPERATURE
            self._attr_min_temp = 16
            self._attr_max_temp = 30
            self._temp_step = 1
            self._attr_target_temperature = 22

        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_hvac_mode = HVACMode.OFF

        self._blaster_actions = data.get(CONF_BLASTER_ACTION, [])

    async def _send_code(self, code: str, repeats: int = 1, delay: float = 0.0) -> None:
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
        else:
            # Turn ON (assuming COOL state or generic ON)
            if self._attr_hvac_mode == HVACMode.OFF and self._power_on_code:
                await self._send_code(self._power_on_code)

            self._attr_hvac_mode = hvac_mode

        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        await self.async_set_hvac_mode(HVACMode.COOL)

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get("temperature")
        if temperature is None or not self._temp_inc_code:
            return

        diff = temperature - self._attr_target_temperature
        steps = int(abs(diff) / self._temp_step)

        code = self._temp_inc_code if diff > 0 else self._temp_dec_code

        if code and steps > 0:
            # SEND WITH 300ms DELAY
            await self._send_code(code, repeats=steps, delay=0.3)

        self._attr_target_temperature = temperature
        self.async_write_ha_state()
