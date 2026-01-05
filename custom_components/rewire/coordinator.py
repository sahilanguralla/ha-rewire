"""Data coordinator for RewIRe devices."""
import logging
from datetime import timedelta
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)


class RewireCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize."""
        self.config_entry = config_entry
        super().__init__(
            hass,
            _LOGGER,
            name="RewIRe",
            update_interval=timedelta(seconds=config_entry.options.get("update_interval", 300)),
        )
        self._device_state: Dict[str, Any] = {
            "power": False,
            "speed": 0,
            "oscillating": False,
            "heat": False,
        }

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from device."""
        try:
            # Coordinator maintains local state since IR is fire-and-forget
            return self._device_state
        except Exception as err:
            raise UpdateFailed(f"Error updating RewIRe: {err}") from err

    def set_device_state(self, state: Dict[str, Any]) -> None:
        """Update internal device state."""
        self._device_state.update(state)
        self.async_set_updated_data(self._device_state)
