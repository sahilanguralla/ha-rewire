"""Base entity for Dyson IR devices."""
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DysonIRCoordinator


class DysonIREntity(CoordinatorEntity[DysonIRCoordinator], Entity):
    """Base entity for Dyson IR devices."""

    def __init__(self, coordinator: DysonIRCoordinator, entry_id: str) -> None:
        """Initialize entity."""
        super().__init__(coordinator)
        self.entry_id = entry_id
        self._attr_unique_id = f"{DOMAIN}_{entry_id}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry_id)},
            name=self.coordinator.config_entry.data.get("name", "Dyson Fan"),
            manufacturer="Dyson",
            model=self.coordinator.config_entry.data.get("device_type", "AM09"),
            via_device=(DOMAIN, self.entry_id),
        )
