"""Tests for the Boks log entry parsing logic."""
import time
from unittest.mock import MagicMock, patch
import pytest
from custom_components.boks.ble.log_entry import BoksLogEntry
from custom_components.boks.ble.const import BoksHistoryEvent, BoksPowerOffReason, BoksDiagnosticErrorCode

# Mock time to ensure consistent timestamps in tests
@pytest.fixture
def mock_time():
    with patch("custom_components.boks.ble.log_entry.time.time") as mock_time:
        mock_time.return_value = 1700000000.0 # Fixed timestamp
        yield mock_time

def test_parse_code_ble_valid(mock_time):
    """Test parsing a valid BLE code event (0x86)."""
    # 0x86 = CODE_BLE_VALID
    # Payload: Age(3 bytes) + Code(6 bytes)
    # Age = 100s -> 0x000064
    # Code = "123456" -> 0x313233343536
    payload = bytes.fromhex("000064313233343536")
    
    entry = BoksLogEntry.from_raw(0x86, bytearray(payload))
    
    assert entry is not None
    assert entry.opcode == BoksHistoryEvent.CODE_BLE_VALID
    assert entry.event_type == "code_ble_valid"
    # 1700000000 - 100 = 1699999900
    assert entry.timestamp == 1699999900
    assert entry.extra_data["code"] == "123456"

def test_parse_code_ble_invalid_hex(mock_time):
    """Test parsing an invalid BLE code with non-printable chars (0x88)."""
    # 0x88 = CODE_BLE_INVALID
    # Payload: Age(3 bytes) + Code(6 bytes)
    # Code = "12\xFF\x0056" (contains non-printable)
    payload = bytes.fromhex("0000643132FF003536")
    
    entry = BoksLogEntry.from_raw(0x88, bytearray(payload))
    
    assert entry is not None
    assert entry.opcode == BoksHistoryEvent.CODE_BLE_INVALID
    assert entry.extra_data["code_hex"] == "3132ff003536"

def test_parse_power_off_watchdog(mock_time):
    """Test parsing a POWER_OFF event due to Watchdog (0x94)."""
    # 0x94 = POWER_OFF
    # Payload: Age(3 bytes) + Reason(1 byte)
    # Reason: 2 (Watchdog)
    payload = bytes.fromhex("00000A02")
    
    entry = BoksLogEntry.from_raw(0x94, bytearray(payload))
    
    assert entry is not None
    assert entry.opcode == BoksHistoryEvent.POWER_OFF
    assert entry.event_type == "power_off"
    assert entry.extra_data["reason_code"] == 2
    assert entry.extra_data["reason_text"] == "WATCHDOG"

def test_parse_power_off_unknown(mock_time):
    """Test parsing a POWER_OFF event with unknown reason."""
    payload = bytes.fromhex("00000A99") # 0x99 is not a valid reason
    
    entry = BoksLogEntry.from_raw(0x94, bytearray(payload))
    
    assert entry is not None
    assert entry.extra_data["reason_text"] == "Unknown (153)"

def test_parse_error_nfc_diagnostic(mock_time):
    """Test parsing an NFC Diagnostic Error (0xA0)."""
    # 0xA0 = ERROR
    # Payload: Age(3 bytes) + Subtype(1 byte) + ErrorCode(1 byte) + Extra...
    # Subtype: 0x08
    # ErrorCode: 0xBC (MFRC630_ERROR_BC)
    payload = bytes.fromhex("00000A08BC001122")
    
    entry = BoksLogEntry.from_raw(0xA0, bytearray(payload))
    
    assert entry is not None
    assert entry.opcode == BoksHistoryEvent.ERROR
    assert entry.extra_data["error_subtype"] == 0x08
    assert entry.extra_data["error_code"] == 0xBC
    assert entry.extra_data["error_description"] == "Erreur interne MFRC630 (0xBC)"
    assert entry.extra_data["error_data"] == "08bc001122"

def test_parse_error_nfc_collision(mock_time):
    """Test parsing an NFC Collision Error (0x0B)."""
    # 0xA0 = ERROR, Subtype 0x08, Error 0x0B (Collision)
    payload = bytes.fromhex("00000A080B")
    
    entry = BoksLogEntry.from_raw(0xA0, bytearray(payload))
    
    assert entry is not None
    assert entry.opcode == BoksHistoryEvent.ERROR
    assert entry.extra_data["error_code"] == 0x0B
    assert entry.extra_data["error_description"] == "Collision de tags détectée"

def test_parse_door_opened(mock_time):
    """Test parsing a simple DOOR_OPENED event (0x91)."""
    # 0x91 = DOOR_OPENED
    # Payload: Age(3 bytes) only
    payload = bytes.fromhex("0000FF")
    
    entry = BoksLogEntry.from_raw(0x91, bytearray(payload))
    
    assert entry is not None
    assert entry.opcode == BoksHistoryEvent.DOOR_OPENED
    assert entry.event_type == "door_opened"

def test_parse_key_opening(mock_time):
    """Test parsing a KEY_OPENING event (0x99)."""
    # 0x99 = KEY_OPENING
    # Payload: Age(3 bytes) + data
    payload = bytes.fromhex("00000A112233")
    
    entry = BoksLogEntry.from_raw(0x99, bytearray(payload))
    
    assert entry is not None
    assert entry.opcode == BoksHistoryEvent.KEY_OPENING
    assert entry.event_type == "key_opening"
    assert entry.extra_data["data"] == "112233"

def test_parse_invalid_opcode():
    """Test parsing an unknown opcode."""
    payload = bytes.fromhex("000000")
    entry = BoksLogEntry.from_raw(0xFF, bytearray(payload))
    assert entry is None

def test_payload_too_short(mock_time):
    """Test parsing with a payload that is too short for the timestamp."""
    payload = bytes.fromhex("00") # Only 1 byte, need 3 for timestamp
    
    entry = BoksLogEntry.from_raw(0x91, bytearray(payload))
    
    assert entry is not None
    # Timestamp should default to now since we couldn't parse age
    assert entry.timestamp == 1700000000
