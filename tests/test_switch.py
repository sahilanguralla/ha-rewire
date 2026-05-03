"""Test rewire switch platform."""

from unittest.mock import MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.rewire.const import (
    ACTION_TYPE_POWER,
    ACTION_TYPE_TOGGLE,
    CONF_ACTIONS,
    CONF_BLASTER_ACTION,
    CONF_DEVICE_TYPE,
    DOMAIN,
)


async def test_switch_creation_and_actions(hass: HomeAssistant):
    """Test that switches are created and can execute actions."""
    # Mock config entry
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry_id"
    config_entry.data = {
        "name": "Test Device",
        CONF_DEVICE_TYPE: "other",
        CONF_BLASTER_ACTION: [
            {
                "service": "remote.send_command",
                "data": {"device_id": "blaster_device_id", "command": "IR_CODE"},
            }
        ],
        CONF_ACTIONS: [
            {
                "name": "Power Toggle",
                "ir_code": "code_toggle",
                "action_type": ACTION_TYPE_TOGGLE,
            },
            {
                "name": "Power Separate",
                "ir_code_on": "code_on",
                "ir_code_off": "code_off",
                "action_type": ACTION_TYPE_POWER,
            },
        ],
    }
    config_entry.options = {"actions_when_off": []}

    # Setup coordinator
    with patch("custom_components.rewire.coordinator.RewireCoordinator.async_config_entry_first_refresh"):
        from custom_components.rewire.coordinator import RewireCoordinator

        coordinator = RewireCoordinator(hass, config_entry)
        hass.data[DOMAIN] = {config_entry.entry_id: coordinator}

    # Setup switch platform
    from custom_components.rewire.switch import async_setup_entry

    async_add_entities = MagicMock()
    await async_setup_entry(hass, config_entry, async_add_entities)

    # Verify entities were added
    assert async_add_entities.called
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 2

    switch_toggle = entities[0]
    switch_separate = entities[1]

    assert switch_toggle.name == "Test Device Power Toggle"
    assert "power_toggle" in switch_toggle.unique_id
    switch_toggle.hass = hass
    switch_toggle.entity_id = "switch.test_device_power_toggle"

    assert switch_separate.name == "Test Device Power Separate"
    switch_separate.hass = hass
    switch_separate.entity_id = "switch.test_device_power_separate"

    # Test initial state (optimistic off)
    assert not switch_toggle.is_on
    assert not switch_separate.is_on

    # Test turn on toggle
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        await switch_toggle.async_turn_on()
        assert switch_toggle.is_on
        mock_call.assert_called_once_with(
            "remote",
            "send_command",
            service_data={
                "device_id": "blaster_device_id",
                "command": ["code_toggle"],
            },
            target=None,
            blocking=True,
        )

    # Test turn off toggle
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        await switch_toggle.async_turn_off()
        assert not switch_toggle.is_on
        mock_call.assert_called_once_with(
            "remote",
            "send_command",
            service_data={
                "device_id": "blaster_device_id",
                "command": ["code_toggle"],
            },
            target=None,
            blocking=True,
        )

    # Test turn on separate
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        await switch_separate.async_turn_on()
        assert switch_separate.is_on
        mock_call.assert_called_once_with(
            "remote",
            "send_command",
            service_data={
                "device_id": "blaster_device_id",
                "command": ["code_on"],
            },
            target=None,
            blocking=True,
        )

    # Test turn off separate
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        await switch_separate.async_turn_off()
        assert not switch_separate.is_on
        mock_call.assert_called_once_with(
            "remote",
            "send_command",
            service_data={
                "device_id": "blaster_device_id",
                "command": ["code_off"],
            },
            target=None,
            blocking=True,
        )


async def test_switch_power_off_fallback(hass: HomeAssistant):
    """Test switch power off fallback to single code."""
    config_entry = MagicMock()
    config_entry.entry_id = "fallback_switch"
    config_entry.data = {
        "name": "Fallback Device",
        CONF_DEVICE_TYPE: "other",
        CONF_BLASTER_ACTION: [
            {"service": "remote.send_command", "data": {"device_id": "blaster_device_id", "command": "IR_CODE"}}
        ],
        CONF_ACTIONS: [
            {
                "name": "Power Fallback",
                "ir_code": "code_single",
                "action_type": ACTION_TYPE_POWER,
                # No ir_code_on or ir_code_off
            }
        ],
    }
    config_entry.options = {}

    with patch("custom_components.rewire.coordinator.RewireCoordinator.async_config_entry_first_refresh"):
        from custom_components.rewire.coordinator import RewireCoordinator

        coordinator = RewireCoordinator(hass, config_entry)
        hass.data[DOMAIN] = {config_entry.entry_id: coordinator}

    from custom_components.rewire.switch import async_setup_entry

    async_add_entities = MagicMock()
    await async_setup_entry(hass, config_entry, async_add_entities)
    switch = async_add_entities.call_args[0][0][0]
    switch.hass = hass
    switch.entity_id = "switch.fallback"

    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        await switch.async_turn_off()
        mock_call.assert_called_with(
            "remote",
            "send_command",
            service_data={"device_id": "blaster_device_id", "command": ["code_single"]},
            target=None,
            blocking=True,
        )
