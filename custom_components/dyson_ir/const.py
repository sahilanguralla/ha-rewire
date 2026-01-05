"""Constants for Dyson IR."""
DOMAIN = "dyson_ir"
PLATFORMS = ["fan", "button", "switch", "number"]

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

# Action Types
ACTION_TYPE_BUTTON = "button"
ACTION_TYPE_POWER = "power"
ACTION_TYPE_TOGGLE = "toggle"
ACTION_TYPE_INC_DEC = "inc_dec"

ACTION_TYPES = [
    ACTION_TYPE_BUTTON,
    ACTION_TYPE_POWER,
    ACTION_TYPE_TOGGLE,
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
