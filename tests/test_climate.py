"""Test rewire climate platform."""

from unittest.mock import MagicMock, patch

from homeassistant.components.climate import ClimateEntityFeature, HVACMode
from homeassistant.core import HomeAssistant

from custom_components.rewire.const import (
    ACTION_TYPE_MODE,
    ACTION_TYPE_OSCILLATE,
    ACTION_TYPE_POWER,
    ACTION_TYPE_SPEED,
    ACTION_TYPE_TEMP,
    CONF_ACTIONS,
    CONF_BLASTER_ACTION,
    CONF_DEVICE_TYPE,
    DEVICE_TYPE_AC,
    DOMAIN,
)


async def test_climate_creation_and_actions(hass: HomeAssistant):
    """Test that climates are created and can execute actions."""
    # Mock config entry
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry_id"
    config_entry.data = {
        "name": "Test Climate Device",
        CONF_DEVICE_TYPE: DEVICE_TYPE_AC,
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
                "name": "Temperature",
                "temp_inc_code": "code_temp_inc",
                "temp_dec_code": "code_temp_dec",
                "min_temp": 16,
                "max_temp": 30,
                "temp_step": 1,
                "temp_unit": "celsius",
                "action_type": ACTION_TYPE_TEMP,
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
            {
                "name": "Mode Cool",
                "ir_code": "code_mode_cool",
                "mode_name": HVACMode.COOL,
                "action_type": ACTION_TYPE_MODE,
            },
            {
                "name": "Mode Heat",
                "ir_code": "code_mode_heat",
                "mode_name": HVACMode.HEAT,
                "action_type": ACTION_TYPE_MODE,
            },
        ],
    }
    config_entry.options = {"actions_when_off": []}

    # Setup coordinator
    with patch("custom_components.rewire.coordinator.RewireCoordinator.async_config_entry_first_refresh"):
        from custom_components.rewire.coordinator import RewireCoordinator

        coordinator = RewireCoordinator(hass, config_entry)
        hass.data[DOMAIN] = {config_entry.entry_id: coordinator}

    # Setup climate platform
    from custom_components.rewire.climate import async_setup_entry

    async_add_entities = MagicMock()
    await async_setup_entry(hass, config_entry, async_add_entities)

    # Verify entities were added
    assert async_add_entities.called
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 1

    climate = entities[0]
    assert climate.name == "Test Climate Device"
    assert "climate" in climate.unique_id
    climate.hass = hass
    climate.entity_id = "climate.test_climate_device"

    # Test initial state (off)
    assert climate.hvac_mode == HVACMode.OFF
    # Supported features when OFF and actions_when_off is empty
    assert climate.supported_features == ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF

    # Test turn on
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        await climate.async_turn_on()
        assert climate.hvac_mode == HVACMode.COOL
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
        climate.supported_features
        == ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.SWING_MODE
    )

    # Test set temperature (increase)
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        current_temp = climate.target_temperature
        await climate.async_set_temperature(temperature=current_temp + 1)
        assert climate.target_temperature == current_temp + 1
        mock_call.assert_called_once_with(
            "remote",
            "send_command",
            service_data={
                "device_id": "blaster_device_id",
                "command": ["code_temp_inc"],
            },
            target=None,
            blocking=True,
        )

    # Test set temperature (decrease)
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        current_temp = climate.target_temperature
        await climate.async_set_temperature(temperature=current_temp - 1)
        assert climate.target_temperature == current_temp - 1
        mock_call.assert_called_once_with(
            "remote",
            "send_command",
            service_data={
                "device_id": "blaster_device_id",
                "command": ["code_temp_dec"],
            },
            target=None,
            blocking=True,
        )

    # Test set fan mode
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        assert climate.fan_mode == "1"
        await climate.async_set_fan_mode("2")
        assert climate.fan_mode == "2"
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

    # Test oscillate / swing mode
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        await climate.async_set_swing_mode("on")
        assert climate.swing_mode == "on"
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

    # Test set hvac mode (heat)
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        await climate.async_set_hvac_mode(HVACMode.HEAT)
        assert climate.hvac_mode == HVACMode.HEAT
        mock_call.assert_called_once_with(
            "remote",
            "send_command",
            service_data={
                "device_id": "blaster_device_id",
                "command": ["code_mode_heat"],
            },
            target=None,
            blocking=True,
        )

    # Test turn off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        await climate.async_turn_off()
        assert climate.hvac_mode == HVACMode.OFF
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


async def test_climate_legacy_config(hass: HomeAssistant):
    """Test climate with legacy config structure."""
    config_entry = MagicMock()
    config_entry.entry_id = "legacy_entry"
    config_entry.data = {
        "name": "Legacy Climate",
        CONF_DEVICE_TYPE: DEVICE_TYPE_AC,
        "power_on_code": "pow_on",
        "power_off_code": "pow_off",
        "temp_inc_code": "t_inc",
        "temp_dec_code": "t_dec",
        "speed_inc_code": "s_inc",
        "speed_dec_code": "s_dec",
        "min_temp": 60,
        "max_temp": 80,
        "temp_step": 2,
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

    from custom_components.rewire.climate import async_setup_entry

    async_add_entities = MagicMock()
    await async_setup_entry(hass, config_entry, async_add_entities)

    climate = async_add_entities.call_args[0][0][0]
    climate.hass = hass
    climate.entity_id = "climate.legacy"

    assert climate.hvac_modes == [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT]

    # Test setting temp returns early if OFF
    climate._attr_hvac_mode = HVACMode.OFF
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        await climate.async_set_temperature(temperature=62)
        assert not mock_call.called

    # Test setting fan returns early if already same
    climate._attr_hvac_mode = HVACMode.COOL
    climate._attr_fan_mode = "1"
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        await climate.async_set_fan_mode("1")
        assert not mock_call.called

    # Test setting swing returns early if already same
    climate._attr_swing_mode = "off"
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        await climate.async_set_swing_mode("off")
        assert not mock_call.called


async def test_climate_initial_state(hass: HomeAssistant):
    """Test climate initial state and temp unit conversion."""
    config_entry = MagicMock()
    config_entry.entry_id = "init_entry"
    config_entry.data = {
        "name": "Init Climate",
        CONF_DEVICE_TYPE: DEVICE_TYPE_AC,
        "initial_state": {
            "current_hvac_mode": "heat",
            "current_temp": 72.0,
            "current_fan_mode": "3",
            "oscillating": True,
        },
        CONF_ACTIONS: [
            {
                "name": "Temperature",
                "temp_inc_code": "t_inc",
                "temp_dec_code": "t_dec",
                "min_temp": 60,
                "max_temp": 90,
                "temp_step": 1,
                "temp_unit": "fahrenheit",
                "action_type": ACTION_TYPE_TEMP,
            },
            {
                "name": "Speed",
                "speed_inc_code": "s_inc",
                "speed_dec_code": "s_dec",
                "min_speed": 1,
                "max_speed": 3,
                "speed_step": 1,
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

    from custom_components.rewire.climate import async_setup_entry

    async_add_entities = MagicMock()
    await async_setup_entry(hass, config_entry, async_add_entities)

    climate = async_add_entities.call_args[0][0][0]
    assert climate.hvac_mode == HVACMode.HEAT
    assert climate.fan_mode == "3"
    assert climate.swing_mode == "on"
