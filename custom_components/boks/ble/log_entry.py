"""Log entry model for Boks."""
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .const import (
    BoksHistoryEvent,
    BoksPowerOffReason,
    LOG_EVENT_DESCRIPTIONS,
    LOG_EVENT_TYPES,
)

_LOGGER = logging.getLogger(__name__)

@dataclass
class BoksLogEntry:
    """Represents a log entry from the Boks device."""
    opcode: BoksHistoryEvent
    payload: bytearray
    timestamp: int # Unix timestamp in seconds
    description: str = "Unknown Event"
    event_type: str = "unknown"
    extra_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_raw(cls, opcode: int, payload: bytearray) -> Optional["BoksLogEntry"]:
        """Parses a raw BLE payload to create a log entry."""
        # Safety check for None payload
        if payload is None:
            _LOGGER.warning("Received None payload for opcode 0x%02X", opcode)
            payload = bytearray()

        _LOGGER.debug("Parsing log entry - Opcode: 0x%02X, Payload: %s", opcode, payload.hex() if payload else "None")

        # Payload structure: [Age (3 bytes), Data...]
        # The timestamp is 'elapsed time' in seconds since the event occurred.

        try:
            event_opcode = BoksHistoryEvent(opcode)
        except ValueError:
            # If opcode is not in our Enum, we might want to handle it gracefully or return None
            # For now, let's treat it as unknown but keep the int value if possible,
            # or just return None if strict typing is required.
            # Given the type hint says opcode: BoksHistoryEvent, we should probably return None
            # or have a fallback 'UNKNOWN' enum member.
            # But to match previous behavior, let's try to proceed if we can,
            # or just return None to be safe.
            return None

        description = LOG_EVENT_DESCRIPTIONS.get(event_opcode, f"Événement inconnu (0x{opcode:02X})")
        event_type = LOG_EVENT_TYPES.get(event_opcode, "unknown")

        timestamp = int(time.time())
        stored_payload = payload

        # Extract elapsed time from the first 3 bytes (Big Endian)
        if len(payload) >= 3:
            try:
                elapsed_seconds = int.from_bytes(payload[0:3], 'big')
                # Sanity check: elapsed time shouldn't be huge (e.g. > 10 years) or negative
                if 0 <= elapsed_seconds < 315360000:
                    timestamp = int(time.time()) - elapsed_seconds

                # The rest is the specific payload
                stored_payload = payload[3:]
            except Exception:
                pass

        extra_data = {}

        # Parsing specific opcodes
        # Codes
        if event_opcode in (
            BoksHistoryEvent.CODE_BLE_VALID,
            BoksHistoryEvent.CODE_KEY_VALID,
            BoksHistoryEvent.CODE_BLE_INVALID,
            BoksHistoryEvent.CODE_KEY_INVALID
        ):
            if len(stored_payload) >= 6:
                # Extract code bytes and handle non-printable characters properly
                code_bytes = stored_payload[0:6]
                try:
                    # Try to decode as ASCII, but if it contains non-printable characters,
                    # represent them as hex values
                    code_str = code_bytes.decode('ascii', errors='ignore')
                    # Check if all characters are valid Boks code characters
                    valid_chars = "0123456789AB"
                    if len(code_str) == 6 and all(c in valid_chars for c in code_str):
                        extra_data["code"] = code_str
                    else:
                        # If not valid, store both the raw bytes and a hex representation
                        extra_data["code"] = code_str
                        extra_data["code_hex"] = code_bytes.hex()
                except UnicodeDecodeError:
                    # If decoding fails completely, store as hex
                    extra_data["code_hex"] = code_bytes.hex()

            # Debug logging to verify extra_data parsing
            _LOGGER.debug("Parsed log entry - Opcode: %s, Extra data: %s", event_opcode, extra_data)

        # Power Off
        elif event_opcode == BoksHistoryEvent.POWER_OFF:
            if len(stored_payload) >= 1:
                reason_code = stored_payload[0]
                extra_data["reason_code"] = reason_code
                try:
                    reason_enum = BoksPowerOffReason(reason_code)
                    extra_data["reason_text"] = reason_enum.name
                except ValueError:
                    extra_data["reason_text"] = f"Unknown ({reason_code})"

        # Error
        elif event_opcode == BoksHistoryEvent.ERROR:
            from .const import ERROR_DESCRIPTIONS, BoksDiagnosticErrorCode

            if len(stored_payload) >= 1:
                # Firmware Analysis: [Subtype:1] [Error:4]
                # Example: A0 08 ... BC 00 ...
                # stored_payload here starts AFTER the timestamp, so index 0 is the subtype/param
                subtype = stored_payload[0]
                extra_data["error_subtype"] = subtype
                
                error_desc = ERROR_DESCRIPTIONS.get("UNKNOWN_ERROR")

                # If payload has enough bytes for an error code (assuming it follows subtype)
                if len(stored_payload) >= 2:
                    # Check for specific error codes at offset 1
                    error_code_byte = stored_payload[1]
                    extra_data["error_code"] = error_code_byte
                    
                    if error_code_byte in list(BoksDiagnosticErrorCode):
                         error_desc = ERROR_DESCRIPTIONS.get(BoksDiagnosticErrorCode(error_code_byte))
                    
                    extra_data["error_data"] = stored_payload.hex()
                
                extra_data["error_description"] = error_desc
                _LOGGER.warning(
                    "Boks reported a diagnostic error: Subtype=0x%02X, Data=%s, Desc=%s",
                    subtype, stored_payload.hex(), error_desc
                )

        # NFC
        elif event_opcode == BoksHistoryEvent.NFC_OPENING:
            # stored_payload: [UID...] or [TYPE][UID...] ?
            # Based on firmware analysis, it seems variable.
            # Safest approach is to store the whole payload as hex for now until confirmed.
            if len(stored_payload) >= 1:
                extra_data["tag_uid"] = stored_payload.hex()

        # NFC Tag Registering Scan (0xA2)
        elif event_opcode == BoksHistoryEvent.NFC_TAG_REGISTERING_SCAN:
             if len(stored_payload) >= 1:
                 extra_data["scan_data"] = stored_payload.hex()

        # Door Events
        elif event_opcode in (BoksHistoryEvent.DOOR_OPENED, BoksHistoryEvent.DOOR_CLOSED):
            pass # No specific payload expected, description is sufficient

        # System Events
        elif event_opcode == BoksHistoryEvent.POWER_ON:
             pass # Often empty or generic

        elif event_opcode == BoksHistoryEvent.BLE_REBOOT:
             pass # Often empty or generic

        elif event_opcode == BoksHistoryEvent.BLOCK_RESET:
             if len(stored_payload) >= 1:
                 extra_data["reset_info"] = stored_payload.hex()

        elif event_opcode == BoksHistoryEvent.HISTORY_ERASE:
             pass

        elif event_opcode == BoksHistoryEvent.LOG_END_HISTORY:
             pass

        # Other Events
        elif event_opcode == BoksHistoryEvent.SCALE_CONTINUOUS_MEASURE:
             if len(stored_payload) >= 1:
                 extra_data["scale_data"] = stored_payload.hex()

        elif event_opcode == BoksHistoryEvent.NFC_ERROR_99:
             if len(stored_payload) >= 1:
                 extra_data["error_info"] = stored_payload.hex()

        # Ensure extra_data is never None (safety check)
        if extra_data is None:
            extra_data = {}

        return cls(
            opcode=event_opcode,
            payload=stored_payload,
            timestamp=timestamp,
            description=description,
            event_type=event_type,
            extra_data=extra_data
        )
