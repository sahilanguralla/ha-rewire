"""Test rewire light platform."""

from unittest.mock import MagicMock, patch

from homeassistant.components.light import ColorMode
from homeassistant.core import HomeAssistant

from custom_components.rewire.const import (
    ACTION_TYPE_BRIGHTNESS,
    ACTION_TYPE_POWER,
    ACTION_TYPE_TOGGLE,
    CONF_ACTIONS,
    CONF_BLASTER_ACTION,
    CONF_DEVICE_TYPE,
    DEVICE_TYPE_LIGHT,
    DOMAIN,
)


async def test_light_creation_and_actions(hass: HomeAssistant):
    """Test that lights are created and can execute actions."""
    # Mock config entry
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry_id"
    config_entry.data = {
        "name": "Test Light Device",
        CONF_DEVICE_TYPE: DEVICE_TYPE_LIGHT,
        CONF_BLASTER_ACTION: [
            {
                "service": "remote.send_command",
                "data": {"device_id": "blaster_device_id", "command": "IR_CODE"},
            }
        ],
        CONF_ACTIONS: [
            {
                "name": "Power",
                "power_on_code": "code_power_on",
                "power_off_code": "code_power_off",
                "action_type": ACTION_TYPE_POWER,
            },
            {
                "name": "Brightness",
                "brightness_inc_code": "code_brightness_inc",
                "brightness_dec_code": "code_brightness_dec",
                "action_type": ACTION_TYPE_BRIGHTNESS,
            },
        ],
    }
    config_entry.options = {"actions_when_off": []}

    # Setup coordinator
    with patch("custom_components.rewire.coordinator.RewireCoordinator.async_config_entry_first_refresh"):
        from custom_components.rewire.coordinator import RewireCoordinator

        coordinator = RewireCoordinator(hass, config_entry)
        hass.data[DOMAIN] = {config_entry.entry_id: coordinator}

    # Setup light platform
    from custom_components.rewire.light import async_setup_entry

    async_add_entities = MagicMock()
    await async_setup_entry(hass, config_entry, async_add_entities)

    # Verify entities were added
    assert async_add_entities.called
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 1

    light = entities[0]
    assert light.name == "Test Light Device"
    assert "light" in light.unique_id
    light.hass = hass
    light.entity_id = "light.test_light_device"

    # Test initial state (off)
    assert not light.is_on
    assert light.supported_color_modes == {ColorMode.BRIGHTNESS}
    assert light.color_mode == ColorMode.BRIGHTNESS

    # Test turn on without brightness
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        await light.async_turn_on()
        assert light.is_on
        mock_call.assert_called_once_with(
            "remote",
            "send_command",
            service_data={
                "device_id": "blaster_device_id",
                "command": ["code_power_on"],
            },
            target=None,
            blocking=True,
        )

    # Test turn on with brightness
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        await light.async_turn_on(brightness=128)
        assert light.is_on
        assert light.brightness == 128
        mock_call.assert_called_once_with(
            "remote",
            "send_command",
            service_data={
                "device_id": "blaster_device_id",
                "command": ["code_power_on"],
            },
            target=None,
            blocking=True,
        )

    # Test turn off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        await light.async_turn_off()
        assert not light.is_on
        mock_call.assert_called_once_with(
            "remote",
            "send_command",
            service_data={
                "device_id": "blaster_device_id",
                "command": ["code_power_off"],
            },
            target=None,
            blocking=True,
        )


async def test_light_legacy_config(hass: HomeAssistant):
    """Test light with legacy config."""
    config_entry = MagicMock()
    config_entry.entry_id = "legacy"
    config_entry.data = {
        "name": "Legacy Light",
        CONF_DEVICE_TYPE: DEVICE_TYPE_LIGHT,
        "power_on_code": "pon",
        "power_off_code": "poff",
        "brightness_inc_code": "binc",
        "brightness_dec_code": "bdec",
        CONF_BLASTER_ACTION: [{"service": "remote.send_command", "data": {"command": "IR_CODE"}}],
    }
    config_entry.options = {}

    with patch("custom_components.rewire.coordinator.RewireCoordinator.async_config_entry_first_refresh"):
        from custom_components.rewire.coordinator import RewireCoordinator

        coordinator = RewireCoordinator(hass, config_entry)
        hass.data[DOMAIN] = {config_entry.entry_id: coordinator}

    from custom_components.rewire.light import async_setup_entry

    async_add_entities = MagicMock()
    await async_setup_entry(hass, config_entry, async_add_entities)
    light = async_add_entities.call_args[0][0][0]

    # Test script fallback and exception by mocking poorly
    light._blaster_actions = [{"script": "dummy"}]
    with patch("homeassistant.helpers.script.Script.async_run", side_effect=Exception("Failed")):
        await light._send_code("test")  # Covers script exception

    light._blaster_actions = [{"service": "invalid.service"}]
    with patch("homeassistant.core.ServiceRegistry.async_call", side_effect=Exception("Failed")):
        await light._send_code("test")  # Covers service exception


async def test_light_initial_state(hass: HomeAssistant):
    """Test light initial state."""
    config_entry = MagicMock()
    config_entry.entry_id = "init_state"
    config_entry.data = {
        "name": "Init Light",
        CONF_DEVICE_TYPE: DEVICE_TYPE_LIGHT,
        "initial_state": {
            "power_state": True,
            "current_brightness": 50,
        },
        CONF_ACTIONS: [{"action_type": ACTION_TYPE_TOGGLE, "ir_code": "tgl"}],
    }
    config_entry.options = {}

    with patch("custom_components.rewire.coordinator.RewireCoordinator.async_config_entry_first_refresh"):
        from custom_components.rewire.coordinator import RewireCoordinator

        coordinator = RewireCoordinator(hass, config_entry)
        hass.data[DOMAIN] = {config_entry.entry_id: coordinator}

    from custom_components.rewire.light import async_setup_entry

    async_add_entities = MagicMock()
    await async_setup_entry(hass, config_entry, async_add_entities)
    light = async_add_entities.call_args[0][0][0]
    light.hass = hass
    light.entity_id = "light.init"

    assert light.is_on
    assert light.brightness == 127

    # Test turn on without power code
    light._power_on_code = None
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        await light.async_turn_on()
        assert not mock_call.called

    # Test turn off without power code
    light._power_off_code = None
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        await light.async_turn_off()
        assert not mock_call.called
