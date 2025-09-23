"""Constants for StormAudio integration."""

DOMAIN = "stormaudio"
DEFAULT_NAME = "StormAudio"
DEFAULT_PORT = 23

# Configuration
CONF_HOST = "host"
CONF_PORT = "port" 
CONF_NAME = "name"

# Discovery
DISCOVERY_TIMEOUT = 5
DISCOVERY_PORT = 23

# API Commands (Based on StormAudio TCP/IP API v23)
CMD_POWER_ON = "ssp.power.on"
CMD_POWER_OFF = "ssp.power.off"
CMD_POWER_QUERY = "ssp.power"
CMD_VOLUME_SET = "ssp.vol."
CMD_VOLUME_QUERY = "ssp.vol"
CMD_VOLUME_UP = "ssp.vol.up"
CMD_VOLUME_DOWN = "ssp.vol.down"
CMD_MUTE_ON = "ssp.mute.on"
CMD_MUTE_OFF = "ssp.mute.off"
CMD_MUTE_QUERY = "ssp.mute"
CMD_MUTE_TOGGLE = "ssp.mute.toggle"
CMD_INPUT_SET = "ssp.input."
CMD_INPUT_QUERY = "ssp.input"
CMD_INPUT_LIST = "ssp.input.list"
CMD_INPUT_NEXT = "ssp.input.next"
CMD_INPUT_PREV = "ssp.input.prev"
CMD_PRESET_SET = "ssp.preset."
CMD_PRESET_QUERY = "ssp.preset"
CMD_PRESET_LIST = "ssp.preset.list"
CMD_DIM_ON = "ssp.dim.on"
CMD_DIM_OFF = "ssp.dim.off"
CMD_DIM_QUERY = "ssp.dim"
CMD_PROC_STATE = "ssp.procstate"
CMD_KEEPALIVE = "ssp.keepalive"

# States
STATE_ON = "on"
STATE_OFF = "off"
