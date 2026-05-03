"""Test rewire config flow."""

from unittest.mock import patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rewire.const import (
    CONF_ACTIONS,
    CONF_BLASTER_ACTION,
    CONF_DEVICE_TYPE,
    DEVICE_TYPE_FAN,
    DOMAIN,
)


async def test_full_config_flow(hass: HomeAssistant):
    """Test the full multi-step config flow."""
    # Step 1: User
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"name": "Test Fan", CONF_DEVICE_TYPE: DEVICE_TYPE_FAN},
    )

    # Step 2: Blaster Device
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "blaster_device"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"blaster_device_id": "mock_device_id"},
    )

    # Step 3: Blaster Action
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "blaster_action"

    action_list = [
        {
            "service": "remote.send_command",
            "target": {"device_id": "mock_device_id"},
            "data": {"command": "IR_CODE"},
        }
    ]
    with (
        patch("homeassistant.helpers.entity_registry.async_get"),
        patch("homeassistant.helpers.entity_registry.async_entries_for_device", return_value=[]),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"selection": "remote.send_command"},
        )

    # Step 4: Actions List (Initially empty, want to add one)
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "actions"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"add_more": True},
    )

    # Step 5: Add Action (Select Type)
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "add_action"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"action_type": "toggle"},
    )

    # Step 6: Configure Action
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "configure_toggle"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"name": "Power On", "ir_code": "dummy_code_1"},
    )

    # Step 7: Actions List (One action added, finish)
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "actions"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"add_more": False},
    )

    # Step 8: Initial State
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "initial_state"

    with patch("custom_components.rewire.async_setup_entry", return_value=True) as mock_setup:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={},
        )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test Fan"
    assert result["data"] == {
        "name": "Test Fan",
        CONF_DEVICE_TYPE: DEVICE_TYPE_FAN,
        "blaster_device_id": "mock_device_id",
        CONF_BLASTER_ACTION: action_list,
        CONF_ACTIONS: [{"name": "Power On", "ir_code": "dummy_code_1", "action_type": "toggle"}],
        "initial_state": {},
    }
    assert len(mock_setup.mock_calls) == 1


async def test_no_actions_error(hass: HomeAssistant):
    """Test error when no actions are added."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"name": "Test", CONF_DEVICE_TYPE: DEVICE_TYPE_FAN},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"blaster_device_id": "mock_device_id"},
    )
    with (
        patch("homeassistant.helpers.entity_registry.async_get"),
        patch("homeassistant.helpers.entity_registry.async_entries_for_device", return_value=[]),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"selection": "remote.send_command"},
        )

    # Try to finish without adding any actions
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"add_more": False})

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "actions"
    assert result["errors"] == {"base": "no_actions"}


async def test_configure_various_actions(hass: HomeAssistant):
    """Test configuring various action types."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"name": "Test Other", CONF_DEVICE_TYPE: "other"},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"blaster_device_id": "mock_device_id"},
    )
    with (
        patch("homeassistant.helpers.entity_registry.async_get"),
        patch("homeassistant.helpers.entity_registry.async_entries_for_device", return_value=[]),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"selection": "remote.send_command"},
        )

    # We are at 'actions' step
    action_types = ["temperature", "speed", "mode", "oscillate", "brightness", "inc_dec", "button"]

    for action_type in action_types:
        result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"add_more": True})
        assert result["step_id"] == "add_action"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"action_type": action_type}
        )

        if action_type == "temperature":
            assert result["step_id"] == "configure_temperature"
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={
                    "temp_inc_code": "INC",
                    "temp_dec_code": "DEC",
                    "min_temp": 16,
                    "max_temp": 30,
                    "temp_step": 1,
                    "temp_unit": "celsius",
                    "delay": 0.5,
                },
            )
        elif action_type == "speed":
            assert result["step_id"] == "configure_speed"
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={
                    "speed_inc_code": "INC",
                    "speed_dec_code": "DEC",
                    "min_speed": 1,
                    "max_speed": 3,
                    "speed_step": 1,
                },
            )
        elif action_type == "mode":
            assert result["step_id"] == "configure_mode"
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={"mode_name": "cool", "ir_code": "COOL_CODE"},
            )
        elif action_type == "oscillate":
            assert result["step_id"] == "configure_oscillate"
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={"name": "Swing", "ir_code": "SWING_CODE"},
            )
        elif action_type == "brightness":
            assert result["step_id"] == "configure_brightness"
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={"brightness_inc_code": "INC", "brightness_dec_code": "DEC"},
            )
        elif action_type == "inc_dec":
            assert result["step_id"] == "configure_action"
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={
                    "name": "Custom Inc",
                    "ir_code_inc": "INC",
                    "ir_code_dec": "DEC",
                    "min_value": 0,
                    "max_value": 10,
                    "step_value": 1,
                },
            )
        elif action_type == "button":
            assert result["step_id"] == "configure_action"
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={"name": "Custom Button", "ir_code": "CODE"},
            )

        assert result["step_id"] == "actions"

    # Also test 'power' again but it exists? Wait, 'power' wasn't added here.
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"add_more": True})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"action_type": "power"})
    assert result["step_id"] == "configure_power"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"separate_codes": True, "power_on_code": "ON", "power_off_code": "OFF"},
    )

    # Now test adding power AGAIN!
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"add_more": True})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"action_type": "power"})
    # It should show error "power_action_exists"
    assert result["step_id"] == "add_action"
    assert result["errors"] == {"base": "power_action_exists"}
    # Continue by adding something else to escape
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"action_type": "button"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"name": "Btn2", "ir_code": "BTN2"}
    )

    # Finish flow
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"add_more": False})

    assert result["step_id"] == "initial_state"
    with patch("custom_components.rewire.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"power_state": False, "current_temp": 22, "oscillating": False, "current_brightness": 100},
        )
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY


async def test_options_flow(hass: HomeAssistant):
    """Test options flow."""
    config_entry = MockConfigEntry(
        version=2,
        domain=DOMAIN,
        title="Test Options",
        data={
            "name": "Test",
            CONF_ACTIONS: [
                {"action_type": "temperature"},
                {"action_type": "speed"},
                {"action_type": "oscillate"},
                {"action_type": "mode"},
                {"action_type": "brightness"},
            ],
        },
        source="user",
        options={},
        entry_id="mock_id",
    )

    config_entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"update_interval": 300, "actions_when_off": ["temperature", "speed"]},
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"] == {"update_interval": 300, "actions_when_off": ["temperature", "speed"]}


async def test_options_flow_legacy(hass: HomeAssistant):
    """Test options flow with legacy actions."""
    config_entry = MockConfigEntry(
        version=2,
        domain=DOMAIN,
        title="Test Options",
        data={
            "name": "Test",
            "temp_inc_code": "inc",
            "temp_dec_code": "dec",
            "speed_inc_code": "inc",
            "speed_dec_code": "dec",
            # Note: oscillate_code in const is "oscillate_code", but legacy checks for "oscillate_code"
            "ir_code": "osc",
            "oscillate_code": "osc",
            "brightness_inc_code": "inc",
            "brightness_dec_code": "dec",
        },
        source="user",
        options={},
        entry_id="mock_id",
    )

    config_entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"update_interval": 300, "actions_when_off": ["temperature", "speed"]},
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
