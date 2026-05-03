"""Test RewIRe coordinator."""

from unittest.mock import MagicMock

from custom_components.rewire.coordinator import RewireCoordinator


async def test_coordinator_update(hass):
    """Test coordinator update and state management."""
    config_entry = MagicMock()
    config_entry.options = {"update_interval": 60}

    coordinator = RewireCoordinator(hass, config_entry)

    # Test update data
    data = await coordinator._async_update_data()
    assert data["power"] is False

    # Test set device state
    coordinator.set_device_state({"power": True})
    assert coordinator.data["power"] is True
