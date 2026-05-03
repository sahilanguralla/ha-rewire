"""Test rewire fan platform."""

from unittest.mock import MagicMock, patch

from homeassistant.components.fan import FanEntityFeature
from homeassistant.core import HomeAssistant

from custom_components.rewire.const import (
    ACTION_TYPE_OSCILLATE,
    ACTION_TYPE_POWER,
    ACTION_TYPE_SPEED,
    CONF_ACTIONS,
    CONF_BLASTER_ACTION,
    CONF_DEVICE_TYPE,
    DEVICE_TYPE_FAN,
    DOMAIN,
)


async def test_fan_creation_and_actions(hass: HomeAssistant):
    """Test that fans are created and can execute actions."""
    # Mock config entry
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry_id"
    config_entry.data = {
        "name": "Test Fan Device",
        CONF_DEVICE_TYPE: DEVICE_TYPE_FAN,
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
                "name": "Speed",
                "speed_inc_code": "code_speed_inc",
                "speed_dec_code": "code_speed_dec",
                "min_speed": 1,
                "max_speed": 3,
                "speed_step": 1,
                "action_type": ACTION_TYPE_SPEED,
            },
            {
                "name": "Oscillate",
                "ir_code": "code_oscillate",
                "action_type": ACTION_TYPE_OSCILLATE,
            },
        ],
    }
    config_entry.options = {"actions_when_off": []}

    # Setup coordinator
    with patch("custom_components.rewire.coordinator.RewireCoordinator.async_config_entry_first_refresh"):
        from custom_components.rewire.coordinator import RewireCoordinator

        coordinator = RewireCoordinator(hass, config_entry)
        hass.data[DOMAIN] = {config_entry.entry_id: coordinator}

    # Setup fan platform
    from custom_components.rewire.fan import async_setup_entry

    async_add_entities = MagicMock()
    await async_setup_entry(hass, config_entry, async_add_entities)

    # Verify entities were added
    assert async_add_entities.called
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 1

    fan = entities[0]
    assert fan.name == "Test Fan Device"
    assert "fan" in fan.unique_id
    fan.hass = hass
    fan.entity_id = "fan.test_fan_device"

    # Test supported features initially (off)
    assert not fan.is_on
    assert fan.supported_features == FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF

    # Test turn on
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        print("Power on code:", fan._power_on_code)
        print("Blaster actions:", fan._blaster_actions)
        await fan.async_turn_on()
        print("After turn on, is_on:", fan.is_on)
        print("After turn on, _attr_is_on:", fan._attr_is_on)
        assert fan.is_on
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

    # Now that it's on, check supported features
    assert (
        fan.supported_features
        == FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.SET_SPEED
        | FanEntityFeature.OSCILLATE
    )

    # Test set percentage (speed up)
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        await fan.async_set_percentage(66)
        assert fan.percentage > 0
        mock_call.assert_called_once_with(
            "remote",
            "send_command",
            service_data={
                "device_id": "blaster_device_id",
                "command": ["code_speed_dec"],
            },
            target=None,
            blocking=True,
        )

    # Test set percentage (speed up)
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        await fan.async_set_percentage(100)
        assert fan.percentage > 66
        mock_call.assert_called_once_with(
            "remote",
            "send_command",
            service_data={
                "device_id": "blaster_device_id",
                "command": ["code_speed_inc"],
            },
            target=None,
            blocking=True,
        )

    # Test oscillate
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        await fan.async_oscillate(True)
        assert fan.oscillating
        mock_call.assert_called_once_with(
            "remote",
            "send_command",
            service_data={
                "device_id": "blaster_device_id",
                "command": ["code_oscillate"],
            },
            target=None,
            blocking=True,
        )

    # Test turn off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        await fan.async_turn_off()
        assert not fan.is_on
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


async def test_fan_legacy_config(hass: HomeAssistant):
    """Test fan with legacy config."""
    config_entry = MagicMock()
    config_entry.entry_id = "legacy_fan"
    config_entry.data = {
        "name": "Legacy Fan",
        CONF_DEVICE_TYPE: DEVICE_TYPE_FAN,
        "power_on_code": "pon",
        "power_off_code": "poff",
        "speed_inc_code": "sinc",
        "speed_dec_code": "sdec",
        "min_speed": 1,
        "max_speed": 5,
        "speed_step": 1,
        CONF_BLASTER_ACTION: [{"service": "remote.send_command", "data": {"command": "IR_CODE"}}],
    }
    config_entry.options = {}

    with patch("custom_components.rewire.coordinator.RewireCoordinator.async_config_entry_first_refresh"):
        from custom_components.rewire.coordinator import RewireCoordinator

        coordinator = RewireCoordinator(hass, config_entry)
        hass.data[DOMAIN] = {config_entry.entry_id: coordinator}

    from custom_components.rewire.fan import async_setup_entry

    async_add_entities = MagicMock()
    await async_setup_entry(hass, config_entry, async_add_entities)
    fan = async_add_entities.call_args[0][0][0]
    fan.hass = hass
    fan.entity_id = "fan.legacy"

    assert fan.percentage_step == 20.0  # 100 / 5


async def test_fan_initial_state(hass: HomeAssistant):
    """Test fan initial state."""
    config_entry = MagicMock()
    config_entry.entry_id = "init_fan"
    config_entry.data = {
        "name": "Init Fan",
        CONF_DEVICE_TYPE: DEVICE_TYPE_FAN,
        "initial_state": {
            "current_speed": 3,
            "oscillating": True,
            "power_state": True,
        },
        CONF_ACTIONS: [
            {
                "name": "Speed",
                "speed_inc_code": "sinc",
                "speed_dec_code": "sdec",
                "min_speed": 1,
                "max_speed": 5,
                "action_type": ACTION_TYPE_SPEED,
            },
            {
                "name": "Oscillate",
                "ir_code": "osc",
                "action_type": ACTION_TYPE_OSCILLATE,
            },
        ],
    }
    config_entry.options = {}

    with patch("custom_components.rewire.coordinator.RewireCoordinator.async_config_entry_first_refresh"):
        from custom_components.rewire.coordinator import RewireCoordinator

        coordinator = RewireCoordinator(hass, config_entry)
        hass.data[DOMAIN] = {config_entry.entry_id: coordinator}

    from custom_components.rewire.fan import async_setup_entry

    async_add_entities = MagicMock()
    await async_setup_entry(hass, config_entry, async_add_entities)
    fan = async_add_entities.call_args[0][0][0]
    fan.hass = hass
    fan.entity_id = "fan.init"

    assert fan.is_on
    assert fan.percentage == 50.0  # (3-1)/(5-1) * 100
    assert fan.oscillating


async def test_fan_percentage_logic(hass: HomeAssistant):
    """Test fan percentage logic (mapping, loops, turn on)."""
    config_entry = MagicMock()
    config_entry.entry_id = "logic_fan"
    config_entry.data = {
        "name": "Logic Fan",
        CONF_DEVICE_TYPE: DEVICE_TYPE_FAN,
        CONF_BLASTER_ACTION: [
            {
                "service": "remote.send_command",
                "data": {"device_id": "blaster_device_id", "command": "IR_CODE"},
            }
        ],
        CONF_ACTIONS: [
            {
                "name": "Power",
                "power_on_code": "pon",
                "power_off_code": "poff",
                "action_type": ACTION_TYPE_POWER,
            },
            {
                "name": "Speed",
                "speed_inc_code": "sinc",
                "speed_dec_code": "sdec",
                "min_speed": 1,
                "max_speed": 5,
                "action_type": ACTION_TYPE_SPEED,
            },
        ],
    }
    config_entry.options = {}

    with patch("custom_components.rewire.coordinator.RewireCoordinator.async_config_entry_first_refresh"):
        from custom_components.rewire.coordinator import RewireCoordinator

        coordinator = RewireCoordinator(hass, config_entry)
        hass.data[DOMAIN] = {config_entry.entry_id: coordinator}

    from custom_components.rewire.fan import async_setup_entry

    async_add_entities = MagicMock()
    await async_setup_entry(hass, config_entry, async_add_entities)
    fan = async_add_entities.call_args[0][0][0]
    fan.hass = hass
    fan.entity_id = "fan.logic"

    # Test setting percentage when off turns it on
    assert not fan.is_on
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        await fan.async_set_percentage(50)
        assert fan.is_on
        # Should call power on (sets pct to 100), then speed dec (one step from 5 to 4)
        assert mock_call.call_count == 2  # Power On + 1 Step (to speed 4)
        assert fan.percentage == 80.0  # Speed 4 is 80% (4/5)

    # Test setting percentage to 0 turns it off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        await fan.async_set_percentage(0)
        assert not fan.is_on
        mock_call.assert_called_with(
            "remote",
            "send_command",
            service_data={"device_id": "blaster_device_id", "command": ["poff"]},
            target=None,
            blocking=True,
        )

    # Test decreasing speed
    await fan.async_turn_on()
    fan._attr_percentage = 100  # Speed 5
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        await fan.async_set_percentage(25)  # Speed 2
        # Diff is negative, sends sdec ONCE (from 5 to 4)
        assert mock_call.call_count == 1
        mock_call.assert_called_with(
            "remote",
            "send_command",
            service_data={"device_id": "blaster_device_id", "command": ["sdec"]},
            target=None,
            blocking=True,
        )
        assert fan.percentage == 80.0  # Speed 4 is 80% (4/5)
