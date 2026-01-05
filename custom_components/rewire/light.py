import copy
import logging
from typing import Any

from homeassistant.components.light import (
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import script
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_BLASTER_ACTION,
    CONF_BRIGHTNESS_DEC_CODE,
    CONF_BRIGHTNESS_INC_CODE,
    CONF_DEVICE_TYPE,
    CONF_POWER_OFF_CODE,
    CONF_POWER_ON_CODE,
    DEVICE_TYPE_LIGHT,
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
    """Set up light entity."""
    coordinator: RewireCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    device_type = config_entry.data.get(CONF_DEVICE_TYPE)

    if device_type != DEVICE_TYPE_LIGHT and device_type != "light":
        return

    async_add_entities([RewireLight(coordinator, config_entry.entry_id)])


class RewireLight(RewireEntity, LightEntity):
    """Light entity aggregating power and brightness."""

    def __init__(
        self,
        coordinator: RewireCoordinator,
        entry_id: str,
    ) -> None:
        """Initialize the light."""
        super().__init__(coordinator, entry_id)

        data = coordinator.config_entry.data

        self._power_on_code = data.get(CONF_POWER_ON_CODE)
        self._power_off_code = data.get(CONF_POWER_OFF_CODE)
        self._brightness_inc_code = data.get(CONF_BRIGHTNESS_INC_CODE)
        self._brightness_dec_code = data.get(CONF_BRIGHTNESS_DEC_CODE)

        self._attr_unique_id = f"{DOMAIN}_{entry_id}_light"
        self._attr_name = data.get("name")
        self._attr_supported_color_modes = {ColorMode.ONOFF}
        self._attr_color_mode = ColorMode.ONOFF

        if self._brightness_inc_code and self._brightness_dec_code:
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
            self._attr_color_mode = ColorMode.BRIGHTNESS

        self._attr_is_on = False
        self._attr_brightness = 255

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

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        if self._power_on_code:
            await self._send_code(self._power_on_code)

        self._attr_is_on = True

        if (brightness := kwargs.get("brightness")) is not None:
            self._attr_brightness = brightness

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        if self._power_off_code:
            await self._send_code(self._power_off_code)

        self._attr_is_on = False
        self.async_write_ha_state()
