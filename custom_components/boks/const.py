"""Constants for the Boks integration."""

DOMAIN = "boks"

# Configuration Constants
CONF_CONFIG_KEY = "config_key"
CONF_MASTER_KEY = "master_key"
CONF_MASTER_CODE = "master_code"
CONF_ANONYMIZE_LOGS = "anonymize_logs"
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

FIRMWARE_MAPPING = {
    "10/125": {
        "4.3.3": "https://boks-dfu.s3.eu-west-3.amazonaws.com/4.3.3/boks_52833/boks_52833_4.3.3_app_dfu.zip"
    }
}

# Timeouts & Delays (Seconds)
TIMEOUT_BLE_CONNECTION = 60.0
TIMEOUT_DOOR_OPEN_MESSAGE = 5 # Time to keep lock held after opening (anti-spam)
TIMEOUT_DOOR_CLOSE = 120.0 # Time to wait for door to close after opening
TIMEOUT_COMMAND_RESPONSE = 10.0
TIMEOUT_LOG_RETRIEVAL_BASE = 15.0 # Minimum timeout for logs
DELAY_POST_DOOR_CLOSE_SYNC = 2.0 # Wait before syncing after door close
DELAY_BATTERY_UPDATE = 1.0 # Wait before updating battery after door events
DELAY_LOG_COUNT_COLLECTION = 2.0 # Time to collect log count notifications
DELAY_RETRY = 0.5 # Delay between retries
DELAY_RETRY_LONG = 2.0 # Longer delay for retries (e.g. generating code)

# Retry Limits
MAX_RETRIES_CODE_GENERATION = 2
MAX_RETRIES_MASTER_CODE_CLEANING = 3
MAX_RETRIES_DEEP_DELETE = 10

# Maintenance
MAX_MASTER_CODE_CLEAN_RANGE = 100
