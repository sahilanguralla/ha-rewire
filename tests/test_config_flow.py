"""Test dyson_ir config flow."""
from unittest.mock import patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant

from custom_components.dyson_ir.const import (
    CONF_ACTIONS,
    CONF_DEVICE_TYPE,
    CONF_IR_BLASTER,
    DEVICE_TYPE_FAN,
    DOMAIN,
)


async def test_full_config_flow(hass: HomeAssistant):
    """Test the full multi-step config flow."""
    # Step 1: User
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"name": "Test Fan", CONF_DEVICE_TYPE: DEVICE_TYPE_FAN},
    )

    # Step 2: Blaster
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "blaster"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_IR_BLASTER: "remote.living_room"},
    )

    # Step 3: Actions List (Initially empty, want to add one)
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "actions"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"add_more": True},
    )

    # Step 4: Add Action
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "add_action"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"name": "Power On", "ir_code": "dummy_code_1"},
    )

    # Step 5: Actions List (One action added, finish)
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "actions"

    with patch(
        "custom_components.dyson_ir.async_setup_entry", return_value=True
    ) as mock_setup:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"add_more": False},
        )

    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == "Test Fan"
    assert result["data"] == {
        "name": "Test Fan",
        CONF_DEVICE_TYPE: DEVICE_TYPE_FAN,
        CONF_IR_BLASTER: "remote.living_room",
        CONF_ACTIONS: [{"name": "Power On", "ir_code": "dummy_code_1"}],
    }
    assert len(mock_setup.mock_calls) == 1


async def test_no_actions_error(hass: HomeAssistant):
    """Test error when no actions are added."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"name": "Test", CONF_DEVICE_TYPE: DEVICE_TYPE_FAN},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_IR_BLASTER: "remote.test"}
    )

    # Try to finish without adding any actions
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"add_more": False}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "actions"
    assert result["errors"] == {"base": "no_actions"}
