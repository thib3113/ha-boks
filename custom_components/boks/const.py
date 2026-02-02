"""Constants for the Boks integration."""
from enum import StrEnum

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

EVENT_LOG = f"{DOMAIN}_log_entry"
EVENT_PARCEL_COMPLETED = f"{DOMAIN}_parcel_completed"
EVENT_LOGS_RETRIEVED = f"{DOMAIN}_logs_retrieved"

class BoksChipset(StrEnum):
    """Boks Chipset Models."""
    NRF52833 = "nRF52833"
    NRF52811 = "nRF52811"

# Hardware Information Map (Internal Firmware Revision -> Info)
BOKS_HARDWARE_INFO = {
    "10/125": {
        "hw_version": "4.0",
        "chipset": BoksChipset.NRF52833,
        "firmwares": {
            "4.2.0": "https://boks-dfu.s3.eu-west-3.amazonaws.com/4.2.0/boks_52833/boks_52833_4.2.0_app_dfu.zip",
            "4.3.3": "https://boks-dfu.s3.eu-west-3.amazonaws.com/4.3.3/boks_52833/boks_52833_4.3.3_app_dfu.zip"
        }
    },
    "10/cd": {
        "hw_version": "3.0",
        "chipset": BoksChipset.NRF52811,
        "firmwares": {
            "4.2.0": "https://boks-dfu.s3.eu-west-3.amazonaws.com/4.2.0/boks_52811/boks_52811_4.2.0_app_dfu.zip",
            "4.3.3": "https://boks-dfu.s3.eu-west-3.amazonaws.com/4.3.3/boks_52811/boks_52811_4.3.3_app_dfu.zip"
        }
    }
}

# Timeouts & Delays (Seconds)
TIMEOUT_BLE_CONNECTION = 60.0
TIMEOUT_DOOR_OPEN_MESSAGE = 5 # Time to keep lock held after opening (anti-spam)
TIMEOUT_DOOR_CLOSE = 120.0 # Time to wait for door to close after opening
TIMEOUT_COMMAND_RESPONSE = 10.0
TIMEOUT_NFC_LISTENING = 6.0 # Time the Boks hardware stays in NFC listening mode
TIMEOUT_NFC_WAIT_RESULT = 7.0 # Security margin for HA to wait for NFC result
TIMEOUT_LOG_RETRIEVAL_BASE = 15.0 # Minimum timeout for logs
TIMEOUT_LOG_COUNT_STABILIZATION = 0.1 # Time to wait for potentially multiple log count responses
DELAY_POST_DOOR_CLOSE_SYNC = 5.0 # Wait before syncing after door close/open
DELAY_BATTERY_UPDATE = 1.0 # Wait before updating battery after door events
DELAY_LOG_COUNT_COLLECTION = 2.0 # Time to collect log count notifications
DELAY_RETRY = 0.5 # Delay between retries
DELAY_RETRY_LONG = 2.0 # Longer delay for retries (e.g. generating code)
MIN_DELAY_BETWEEN_CONNECTIONS = 2.0 # Wait between disconnect and next connect for ESP proxy stability

# Retry Limits
MAX_RETRIES_CODE_GENERATION = 2
MAX_RETRIES_MASTER_CODE_CLEANING = 3
MAX_RETRIES_DEEP_DELETE = 10

# Maintenance
MAX_MASTER_CODE_CLEAN_RANGE = 100

# Firmware Update Constants
UPDATE_WWW_DIR = "boks"
UPDATE_ASSETS_DIR = "assets"
UPDATE_FIRMWARE_DIR = "firmware"
UPDATE_JSON_FILENAME = "versions.json"
UPDATE_INDEX_FILENAME = "index.html"
UPDATE_NOTIFICATION_ID_PREFIX = "boks_update_"
UPDATE_LOCAL_URL_PREFIX = f"/local/{UPDATE_WWW_DIR}"

# HTML Template Placeholders
TPL_STYLE = "[[STYLE_CSS]]"
TPL_NORDIC_LIB = "[[NORDIC_DFU_JS]]"
TPL_TRANSLATIONS = "[[TRANSLATIONS_JS]]"
TPL_UPDATER = "[[UPDATER_JS]]"
TPL_TARGET_VER = "[[TARGET_VERSION]]"
TPL_EXPECTED_HW = "[[EXPECTED_HW_VERSION]]"
TPL_INTERNAL_REV = "[[EXPECTED_INTERNAL_REV]]"
TPL_FW_FILENAME = "[[FIRMWARE_FILENAME]]"
