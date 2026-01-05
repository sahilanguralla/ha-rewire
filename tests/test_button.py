"""Test rewire button platform."""
from unittest.mock import MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.rewire.const import (
    CONF_ACTIONS,
    CONF_BLASTER_ACTION,
    DOMAIN,
)


async def test_button_creation_and_press(hass: HomeAssistant):
    """Test that buttons are created and can be pressed."""
    # Mock config entry
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry_id"
    config_entry.data = {
        "name": "Test Device",
        CONF_BLASTER_ACTION: [
            {
                "service": "remote.send_command",
                "data": {"device_id": "blaster_device_id", "command": "IR_CODE"},
            }
        ],
        CONF_ACTIONS: [
            {"name": "Power On", "ir_code": "code_on"},
            {"name": "Power Off", "ir_code": "code_off"},
        ],
    }

    # Setup coordinator
    with patch("custom_components.rewire.coordinator.RewireCoordinator.async_config_entry_first_refresh"):
        from custom_components.rewire.coordinator import RewireCoordinator

        coordinator = RewireCoordinator(hass, config_entry)
        hass.data[DOMAIN] = {config_entry.entry_id: coordinator}

    # Setup button platform
    from custom_components.rewire.button import async_setup_entry

    async_add_entities = MagicMock()
    await async_setup_entry(hass, config_entry, async_add_entities)

    # Verify entities were added
    assert async_add_entities.called
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 2

    button_on = entities[0]
    assert button_on.name == "Test Device Power On"
    assert "power_on" in button_on.unique_id

    # Test pressing the button
    with patch.object(hass.services, "async_call") as mock_call:
        await button_on.async_press()

        mock_call.assert_called_once_with(
            "remote",
            "send_command",
            {
                "device_id": "blaster_device_id",
                "command": ["code_on"],
            },
        )
