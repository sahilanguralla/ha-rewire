"""Test rewire number platform."""

from unittest.mock import MagicMock, patch

from homeassistant.components.number import NumberMode
from homeassistant.core import HomeAssistant

from custom_components.rewire.const import (
    ACTION_TYPE_INC_DEC,
    ACTION_TYPE_SPEED,
    CONF_ACTIONS,
    CONF_BLASTER_ACTION,
    CONF_DEVICE_TYPE,
    DEVICE_TYPE_AC,
    DOMAIN,
)


async def test_number_creation_and_actions(hass: HomeAssistant):
    """Test that numbers are created and can execute actions."""
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
                "name": "Custom Number",
                "ir_code_inc": "code_inc",
                "ir_code_dec": "code_dec",
                "min_value": 1,
                "max_value": 5,
                "step_value": 1,
                "action_type": ACTION_TYPE_INC_DEC,
            },
        ],
    }
    config_entry.options = {"actions_when_off": []}

    # Setup coordinator
    with patch("custom_components.rewire.coordinator.RewireCoordinator.async_config_entry_first_refresh"):
        from custom_components.rewire.coordinator import RewireCoordinator

        coordinator = RewireCoordinator(hass, config_entry)
        hass.data[DOMAIN] = {config_entry.entry_id: coordinator}

    # Setup number platform
    from custom_components.rewire.number import async_setup_entry

    async_add_entities = MagicMock()
    await async_setup_entry(hass, config_entry, async_add_entities)

    # Verify entities were added
    assert async_add_entities.called
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 1

    number = entities[0]
    assert number.name == "Test Device Custom Number"
    assert "custom_number" in number.unique_id
    number.hass = hass
    number.entity_id = "number.test_device_custom_number"

    # Test initial state (middle of range)
    # min=1, max=5 -> (1+5)/2 = 3.0
    assert number.native_value == 3.0
    assert number.native_min_value == 1.0
    assert number.native_max_value == 5.0
    assert number.native_step == 1.0
    assert number.mode == NumberMode.SLIDER

    # Test set value (increase)
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        await number.async_set_native_value(4.0)
        assert number.native_value == 4.0
        mock_call.assert_called_once_with(
            "remote",
            "send_command",
            service_data={
                "device_id": "blaster_device_id",
                "command": ["code_inc"],
            },
            target=None,
            blocking=True,
        )

    # Test set value (decrease)
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        await number.async_set_native_value(2.0)
        # Note: logic only moves by 1 step (diff < 0 -> step=1, dir=-1)
        # So value will be 4.0 - 1.0 = 3.0
        assert number.native_value == 3.0
        mock_call.assert_called_once_with(
            "remote",
            "send_command",
            service_data={
                "device_id": "blaster_device_id",
                "command": ["code_dec"],
            },
            target=None,
            blocking=True,
        )


async def test_number_ac_availability(hass: HomeAssistant):
    """Test availability check for AC devices."""
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry_id_ac"
    config_entry.data = {
        "name": "Test AC",
        CONF_DEVICE_TYPE: DEVICE_TYPE_AC,
        CONF_ACTIONS: [
            {
                "name": "Speed",
                "speed_inc_code": "code_speed_inc",
                "speed_dec_code": "code_speed_dec",
                "action_type": ACTION_TYPE_SPEED,
            },
        ],
    }
    config_entry.options = {}

    with patch("custom_components.rewire.coordinator.RewireCoordinator.async_config_entry_first_refresh"):
        from custom_components.rewire.coordinator import RewireCoordinator

        coordinator = RewireCoordinator(hass, config_entry)
        hass.data[DOMAIN] = {config_entry.entry_id: coordinator}

    from custom_components.rewire.number import async_setup_entry

    async_add_entities = MagicMock()
    await async_setup_entry(hass, config_entry, async_add_entities)

    entities = async_add_entities.call_args[0][0]
    number = entities[0]

    # Initially power is False in coordinator.data
    coordinator.data = {"power": False}
    assert not number.available

    coordinator.data = {"power": True}
    assert number.available


async def test_number_legacy_ac_fan(hass: HomeAssistant):
    """Test legacy AC fan speed number creation."""
    config_entry = MagicMock()
    config_entry.entry_id = "legacy_ac"
    config_entry.data = {
        "name": "Legacy AC",
        CONF_DEVICE_TYPE: DEVICE_TYPE_AC,
        "speed_inc_code": "sinc",
        "speed_dec_code": "sdec",
        "min_speed": 1,
        "max_speed": 5,
        "speed_step": 1,
    }
    config_entry.options = {}

    with patch("custom_components.rewire.coordinator.RewireCoordinator.async_config_entry_first_refresh"):
        from custom_components.rewire.coordinator import RewireCoordinator

        coordinator = RewireCoordinator(hass, config_entry)
        hass.data[DOMAIN] = {config_entry.entry_id: coordinator}

    from custom_components.rewire.number import async_setup_entry

    async_add_entities = MagicMock()
    await async_setup_entry(hass, config_entry, async_add_entities)
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 1
    assert entities[0]._action_name == "Fan Speed"


async def test_number_restore_state(hass: HomeAssistant):
    """Test number restore state."""
    config_entry = MagicMock()
    config_entry.entry_id = "restore_num"
    config_entry.data = {
        "name": "Restore Number",
        CONF_DEVICE_TYPE: "other",
        CONF_ACTIONS: [
            {
                "name": "Value",
                "ir_code_inc": "inc",
                "ir_code_dec": "dec",
                "action_type": ACTION_TYPE_INC_DEC,
            }
        ],
    }
    config_entry.options = {}

    with patch("custom_components.rewire.coordinator.RewireCoordinator.async_config_entry_first_refresh"):
        from custom_components.rewire.coordinator import RewireCoordinator

        coordinator = RewireCoordinator(hass, config_entry)
        hass.data[DOMAIN] = {config_entry.entry_id: coordinator}

    from custom_components.rewire.number import async_setup_entry

    async_add_entities = MagicMock()
    await async_setup_entry(hass, config_entry, async_add_entities)
    number = async_add_entities.call_args[0][0][0]
    number.hass = hass

    with patch(
        "homeassistant.helpers.restore_state.RestoreEntity.async_get_last_state", return_value=MagicMock(state="25.0")
    ):
        await number.async_added_to_hass()
        assert number.native_value == 25.0

    with patch(
        "homeassistant.helpers.restore_state.RestoreEntity.async_get_last_state",
        return_value=MagicMock(state="invalid"),
    ):
        await number.async_added_to_hass()
        # Should keep last valid value (25.0)
        assert number.native_value == 25.0
