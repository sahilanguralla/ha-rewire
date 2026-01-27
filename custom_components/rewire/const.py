"""Constants for RewIRe."""
from typing import Final

DOMAIN = "rewire"

PLATFORMS: Final[list[str]] = [
    "button",
    "switch",
    "number",
    "fan",
    "climate",
    "light",
]

# Device types
DEVICE_TYPE_FAN = "fan"
DEVICE_TYPE_LIGHT = "light"
DEVICE_TYPE_AC = "ac"

DEVICE_TYPES = [DEVICE_TYPE_FAN, DEVICE_TYPE_LIGHT, DEVICE_TYPE_AC]

# Configuration keys
CONF_ACTIONS = "actions"
CONF_ACTION_NAME = "name"
CONF_ACTION_CODE = "ir_code"
CONF_DEVICE_ID = "device_id"
CONF_BLASTER_ACTION = "blaster_action"
CONF_DEVICE_TYPE = "device_type"
CONF_ACTION_TYPE = "action_type"
CONF_ACTION_CODE_ON = "ir_code_on"
CONF_ACTION_CODE_OFF = "ir_code_off"
CONF_ACTION_CODE_INC = "ir_code_inc"
CONF_ACTION_CODE_DEC = "ir_code_dec"
CONF_MIN_VALUE = "min_value"
CONF_MAX_VALUE = "max_value"
CONF_STEP_VALUE = "step_value"
CONF_MIN_TEMP = "min_temp"
CONF_MAX_TEMP = "max_temp"
CONF_TEMP_STEP = "temp_step"
CONF_MIN_SPEED = "min_speed"
CONF_MAX_SPEED = "max_speed"
CONF_SPEED_STEP = "speed_step"

# Action Types
ACTION_TYPE_BUTTON = "button"
ACTION_TYPE_POWER = "power"
ACTION_TYPE_TOGGLE = "toggle"
ACTION_TYPE_TEMP = "temperature"
ACTION_TYPE_MODE = "mode"
ACTION_TYPE_SPEED = "speed"
ACTION_TYPE_OSCILLATE = "oscillate"
ACTION_TYPE_BRIGHTNESS = "brightness"
ACTION_TYPE_INC_DEC = "inc_dec"

ACTION_TYPES = [
    ACTION_TYPE_BUTTON,
    ACTION_TYPE_POWER,
    ACTION_TYPE_TOGGLE,
    ACTION_TYPE_TEMP,
    ACTION_TYPE_MODE,
    ACTION_TYPE_SPEED,
    ACTION_TYPE_OSCILLATE,
    ACTION_TYPE_BRIGHTNESS,
    ACTION_TYPE_INC_DEC,
]

# Speed settings
SPEED_OFF = 0
SPEED_LOW = 33
SPEED_MEDIUM = 66
SPEED_HIGH = 100

# Update intervals (seconds)
COORDINATOR_UPDATE_INTERVAL = 300

# Device attributes
ATTR_OSCILLATING = "oscillating"
ATTR_SPEED = "speed"
ATTR_MODE = "mode"

# Template Config Keys
CONF_POWER_ON_CODE = "power_on_code"
CONF_POWER_OFF_CODE = "power_off_code"
CONF_POWER_TOGGLE_CODE = "power_toggle_code"

# Fan Specific
CONF_OSCILLATE_CODE = "oscillate_code"
CONF_SPEED_INC_CODE = "speed_inc_code"
CONF_SPEED_DEC_CODE = "speed_dec_code"

# Climate Specific
CONF_TEMP_INC_CODE = "temp_inc_code"
CONF_TEMP_DEC_CODE = "temp_dec_code"

# Light Specific
CONF_BRIGHTNESS_INC_CODE = "brightness_inc_code"
CONF_BRIGHTNESS_DEC_CODE = "brightness_dec_code"
