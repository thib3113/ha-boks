"""Constants for Boks BLE communication."""
from enum import IntEnum, StrEnum

class BoksServiceUUID(StrEnum):
    """UUIDs for Boks services and characteristics."""
    SERVICE = "a7630001-f491-4f21-95ea-846ba586e361"
    WRITE_CHARACTERISTIC = "a7630002-f491-4f21-95ea-846ba586e361"
    NOTIFY_CHARACTERISTIC = "a7630003-f491-4f21-95ea-846ba586e361"
    BATTERY_CHARACTERISTIC = "00000004-0000-1000-8000-00805f9b34fb"

    BATTERY_SERVICE = "0000180f-0000-1000-8000-00805f9b34fb"
    BATTERY_LEVEL_CHARACTERISTIC = "00002a19-0000-1000-8000-00805f9b34fb"

    DEVICE_INFO_SERVICE = "0000180a-0000-1000-8000-00805f9b34fb"
    SYSTEM_ID_CHARACTERISTIC = "00002a23-0000-1000-8000-00805f9b34fb"
    MODEL_NUMBER_CHARACTERISTIC = "00002a24-0000-1000-8000-00805f9b34fb"
    SERIAL_NUMBER_CHARACTERISTIC = "00002a25-0000-1000-8000-00805f9b34fb"
    INTERNAL_FIRMWARE_REVISION_CHARACTERISTIC = "00002a26-0000-1000-8000-00805f9b34fb"
    HARDWARE_REVISION_CHARACTERISTIC = "00002a27-0000-1000-8000-00805f9b34fb"
    SOFTWARE_REVISION_CHARACTERISTIC = "00002a28-0000-1000-8000-00805f9b34fb"
    MANUFACTURER_NAME_CHARACTERISTIC = "00002a29-0000-1000-8000-00805f9b34fb"

class BoksCommandOpcode(IntEnum):
    """Opcodes for commands sent to the Boks (Downlink)."""
    OPEN_DOOR = 0x01
    ASK_DOOR_STATUS = 0x02
    REQUEST_LOGS = 0x03
    REBOOT = 0x06
    GET_LOGS_COUNT = 0x07
    TEST_BATTERY = 0x08
    MASTER_CODE_EDIT = 0x09
    SINGLE_USE_CODE_TO_MULTI = 0x0A
    MULTI_CODE_TO_SINGLE_USE = 0x0B
    DELETE_MASTER_CODE = 0x0C
    DELETE_SINGLE_USE_CODE = 0x0D
    DELETE_MULTI_USE_CODE = 0x0E
    REACTIVATE_CODE = 0x0F
    GENERATE_CODES = 0x10
    CREATE_MASTER_CODE = 0x11
    CREATE_SINGLE_USE_CODE = 0x12
    CREATE_MULTI_USE_CODE = 0x13
    COUNT_CODES = 0x14
    GENERATE_CODES_SUPPORT = 0x15
    SET_CONFIGURATION = 0x16
    REGISTER_NFC_TAG_SCAN_START = 0x17
    REGISTER_NFC_TAG = 0x18
    UNREGISTER_NFC_TAG = 0x19

class BoksNotificationOpcode(IntEnum):
    """Opcodes for notifications received from the Boks (Uplink)."""
    CODE_OPERATION_SUCCESS = 0x77
    CODE_OPERATION_ERROR = 0x78
    NOTIFY_LOGS_COUNT = 0x79
    ERROR_COMMAND_NOT_SUPPORTED = 0x80
    VALID_OPEN_CODE = 0x81
    INVALID_OPEN_CODE = 0x82
    NOTIFY_DOOR_STATUS = 0x84
    ANSWER_DOOR_STATUS = 0x85
    NOTIFY_CODE_GENERATION_SUCCESS = 0xC0
    NOTIFY_CODE_GENERATION_ERROR = 0xC1
    NOTIFY_CODES_COUNT = 0xC3
    NOTIFY_SET_CONFIGURATION_SUCCESS = 0xC4
    ERROR_CRC = 0xE0
    ERROR_UNAUTHORIZED = 0xE1
    ERROR_BAD_REQUEST = 0xE2

class BoksHistoryEvent(IntEnum):
    """Opcodes for history events (logs)."""
    CODE_BLE_VALID = 0x86
    CODE_KEY_VALID = 0x87
    CODE_BLE_INVALID = 0x88
    CODE_KEY_INVALID = 0x89
    DOOR_CLOSED = 0x90
    DOOR_OPENED = 0x91
    LOG_END_HISTORY = 0x92
    HISTORY_ERASE = 0x93
    POWER_OFF = 0x94
    BLOCK_RESET = 0x95
    POWER_ON = 0x96
    BLE_REBOOT = 0x97
    SCALE_CONTINUOUS_MEASURE = 0x98
    NFC_ERROR_99 = 0x99
    ERROR = 0xA0
    NFC_OPENING = 0xA1
    NFC_TAG_REGISTERING_SCAN = 0xA2

class BoksPowerOffReason(IntEnum):
    """Reason codes for POWER_OFF event."""
    PIN_RESET = 1
    WATCHDOG = 2
    SOFT_RESET = 3
    LOCKUP = 4
    POWER_ON = 5
    WAKEUP_NFC = 6
    WAKEUP_SYSTEM_OFF = 7
    WAKEUP_LPCOMP = 8

class BoksDiagnosticErrorCode(IntEnum):
    """Specific error codes for diagnostic events (0xA0)."""
    MFRC630_ERROR_BC = 0xBC
    MFRC630_ERROR_INTEGRITY = 0x13
    MFRC630_ERROR_NO_TAG = 0x15
    MFRC630_ERROR_COLLISION = 0x0B
    MFRC630_ERROR_BUFFER = 0x03

ERROR_DESCRIPTIONS = {
    BoksDiagnosticErrorCode.MFRC630_ERROR_BC: "Erreur interne MFRC630 (0xBC)",
    BoksDiagnosticErrorCode.MFRC630_ERROR_INTEGRITY: "Erreur d'intégrité (CRC/Parité)",
    BoksDiagnosticErrorCode.MFRC630_ERROR_NO_TAG: "Aucun tag détecté / Timeout",
    BoksDiagnosticErrorCode.MFRC630_ERROR_COLLISION: "Collision de tags détectée",
    BoksDiagnosticErrorCode.MFRC630_ERROR_BUFFER: "Dépassement de mémoire tampon (Buffer Overflow)",
    "UNKNOWN_ERROR": "Erreur technique inconnue",
}

LOG_EVENT_DESCRIPTIONS = {
    BoksHistoryEvent.CODE_BLE_VALID: "code_ble_valid",
    BoksHistoryEvent.CODE_KEY_VALID: "code_key_valid",
    BoksHistoryEvent.CODE_BLE_INVALID: "code_ble_invalid",
    BoksHistoryEvent.CODE_KEY_INVALID: "code_key_invalid",
    BoksHistoryEvent.DOOR_CLOSED: "door_closed",
    BoksHistoryEvent.DOOR_OPENED: "door_opened",
    BoksHistoryEvent.HISTORY_ERASE: "history_erase",
    BoksHistoryEvent.POWER_OFF: "power_off",
    BoksHistoryEvent.BLOCK_RESET: "block_reset",
    BoksHistoryEvent.POWER_ON: "power_on",
    BoksHistoryEvent.BLE_REBOOT: "ble_reboot",
    BoksHistoryEvent.SCALE_CONTINUOUS_MEASURE: "scale_measure",
    BoksHistoryEvent.NFC_ERROR_99: "nfc_error_99",
    BoksHistoryEvent.ERROR: "error",
    BoksHistoryEvent.NFC_OPENING: "nfc_opening",
    BoksHistoryEvent.NFC_TAG_REGISTERING_SCAN: "nfc_tag_registering_scan",
}

LOG_EVENT_TYPES = {
    BoksHistoryEvent.CODE_BLE_VALID: "code_ble_valid",
    BoksHistoryEvent.CODE_KEY_VALID: "code_key_valid",
    BoksHistoryEvent.CODE_BLE_INVALID: "code_ble_invalid",
    BoksHistoryEvent.CODE_KEY_INVALID: "code_key_invalid",
    BoksHistoryEvent.DOOR_CLOSED: "door_closed",
    BoksHistoryEvent.DOOR_OPENED: "door_opened",
    BoksHistoryEvent.HISTORY_ERASE: "history_erase",
    BoksHistoryEvent.POWER_OFF: "power_off",
    BoksHistoryEvent.BLOCK_RESET: "block_reset",
    BoksHistoryEvent.POWER_ON: "power_on",
    BoksHistoryEvent.BLE_REBOOT: "ble_reboot",
    BoksHistoryEvent.SCALE_CONTINUOUS_MEASURE: "scale_measure",
    BoksHistoryEvent.NFC_ERROR_99: "nfc_error_transaction",
    BoksHistoryEvent.ERROR: "error",
    BoksHistoryEvent.NFC_OPENING: "nfc_opening",
    BoksHistoryEvent.NFC_TAG_REGISTERING_SCAN: "nfc_tag_registering",
}

class BoksCodeType(StrEnum):
    """Code types for Boks."""
    MASTER = "master"
    SINGLE_USE = "single_use"
    MULTI_USE = "multi_use"

class BoksConfigType(IntEnum):
    """Configuration types for Boks (SET_CONFIGURATION)."""
    SCAN_LAPOSTE_NFC_TAGS = 0x01
