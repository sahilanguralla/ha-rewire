"""Constants for Dyson IR."""
DOMAIN = "dyson_ir"
PLATFORMS = ["fan"]

# Device types
DEVICE_TYPE_FAN = "fan"
DEVICE_TYPE_LIGHT = "light"
DEVICE_TYPE_AC = "ac"

DEVICE_TYPES = [DEVICE_TYPE_FAN, DEVICE_TYPE_LIGHT, DEVICE_TYPE_AC]

# Configuration keys
CONF_ACTIONS = "actions"
CONF_ACTION_NAME = "name"
CONF_ACTION_CODE = "ir_code"
CONF_IR_BLASTER = "ir_blaster_entity"
CONF_DEVICE_TYPE = "device_type"

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
