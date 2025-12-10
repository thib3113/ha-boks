"""Constants for the Boks integration."""

DOMAIN = "boks"

# Configuration Constants
CONF_CONFIG_KEY = "config_key"
CONF_MASTER_KEY = "master_key"
CONF_MASTER_CODE = "master_code"
CONF_AUTH_METHOD = "auth_method"
BOKS_CHAR_MAP = "0123456789AB"

# Defaults
DEFAULT_SCAN_INTERVAL = 10
DEFAULT_FULL_REFRESH_INTERVAL = 12

EVENT_LOG = "boks_log_entry"
EVENT_PARCEL_COMPLETED = "boks_parcel_completed"

# Hardware Revisions Map (Internal Firmware Revision -> Hardware Version)
PCB_VERSIONS = {
    "10/125": "4.0",
    "10/cd": "3.0"
}
