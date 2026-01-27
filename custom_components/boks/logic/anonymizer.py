"""Anonymization utilities for Boks."""
from typing import Optional

from ..ble.const import BoksCommandOpcode, BoksHistoryEvent, BoksNotificationOpcode
from ..ble.protocol import BoksProtocol

# Placeholders
FAKE_PIN_STR = "******"
FAKE_KEY_STR = "********"
FAKE_PIN_BYTES = b"1234AB"
FAKE_KEY_BYTES = b"1A3B5C7E"
FAKE_UID_BYTE = 0x55

class BoksAnonymizer:
    """Helper class to anonymize sensitive data in packets and strings."""

    @staticmethod
    def anonymize_uid(uid: Optional[str], anonymize: bool = True) -> Optional[str]:
        """Mask an NFC UID (e.g. 5A3EDAE0 -> 5A...E0) for display if anonymize is True."""
        if not uid or not anonymize:
            return uid or "None" if not uid else uid

        if len(uid) <= 4:
            return "***"
        return f"{uid[:2]}...{uid[-2:]}"

    @staticmethod
    def anonymize_pin(pin: Optional[str], anonymize: bool = True) -> Optional[str]:
        """Mask a 6-character PIN if anonymize is True."""
        if not pin or not anonymize:
            return pin
        return FAKE_PIN_STR

    @staticmethod
    def anonymize_key(key: Optional[str], anonymize: bool = True) -> Optional[str]:
        """Mask an 8-character Config Key if anonymize is True."""
        if not key or not anonymize:
            return key
        return FAKE_KEY_STR

    @staticmethod
    def anonymize_packet(data: Optional[bytearray], anonymize: bool = True) -> Optional[bytearray]:
        """
        Create a version of the packet with sensitive data replaced by placeholders.
        Only performs anonymization if anonymize is True.
        Recalculates the checksum at the end if modified.
        """
        if data is None or not anonymize:
            return data

        faked = bytearray(data)
        if len(faked) < 3:
            return faked

        opcode = faked[0]
        length = faked[1]
        modified = False

        # 1. Handle commands (Downlink)
        if opcode == BoksCommandOpcode.OPEN_DOOR and length >= 6:
            faked[2:8] = FAKE_PIN_BYTES
            modified = True
        elif BoksAnonymizer._is_key_based_command(opcode):
            modified = BoksAnonymizer._anonymize_command_with_key(faked, opcode, length)
        # 2. Handle History events (Uplink)
        elif BoksAnonymizer._is_pin_based_history(opcode):
            if length >= 6:
                faked[2:8] = FAKE_PIN_BYTES
                modified = True
        elif opcode in (BoksHistoryEvent.NFC_OPENING, BoksNotificationOpcode.NOTIFY_NFC_TAG_FOUND):
            modified = BoksAnonymizer._anonymize_nfc_payload(faked, opcode)

        # 3. Recalculate checksum if modified
        if modified:
            faked[-1] = BoksProtocol.calculate_checksum(faked[:-1])

        return faked

    @staticmethod
    def _is_key_based_command(opcode: int) -> bool:
        """Check if an opcode corresponds to a command requiring a ConfigKey."""
        return opcode in (
            BoksCommandOpcode.CREATE_MASTER_CODE,
            BoksCommandOpcode.CREATE_SINGLE_USE_CODE,
            BoksCommandOpcode.CREATE_MULTI_USE_CODE,
            BoksCommandOpcode.MASTER_CODE_EDIT,
            BoksCommandOpcode.DELETE_MASTER_CODE,
            BoksCommandOpcode.DELETE_SINGLE_USE_CODE,
            BoksCommandOpcode.DELETE_MULTI_USE_CODE,
            BoksCommandOpcode.SET_CONFIGURATION,
            BoksCommandOpcode.GENERATE_CODES,
            BoksCommandOpcode.REGISTER_NFC_TAG_SCAN_START,
            BoksCommandOpcode.REGISTER_NFC_TAG,
            BoksCommandOpcode.UNREGISTER_NFC_TAG
        )

    @staticmethod
    def _anonymize_command_with_key(faked: bytearray, opcode: int, length: int) -> bool:
        """Anonymize commands starting with an 8-byte ConfigKey."""
        if length < 8:
            return False
            
        faked[2:10] = FAKE_KEY_BYTES
        
        # Dispatch to specific sub-anonymizers
        if opcode in (BoksCommandOpcode.CREATE_MASTER_CODE, BoksCommandOpcode.CREATE_SINGLE_USE_CODE, BoksCommandOpcode.CREATE_MULTI_USE_CODE):
            BoksAnonymizer._mask_pin_at_offset(faked, length, 10)
        elif opcode == BoksCommandOpcode.MASTER_CODE_EDIT:
            BoksAnonymizer._mask_pin_at_offset(faked, length, 11)
        elif opcode in (BoksCommandOpcode.REGISTER_NFC_TAG, BoksCommandOpcode.UNREGISTER_NFC_TAG):
            BoksAnonymizer._mask_uid_at_offset(faked, length, 10)
            
        return True

    @staticmethod
    def _mask_pin_at_offset(faked: bytearray, length: int, offset: int) -> None:
        """Mask a 6-byte PIN at a specific offset."""
        if length >= offset + 6:
            faked[offset : offset + 6] = FAKE_PIN_BYTES

    @staticmethod
    def _mask_uid_at_offset(faked: bytearray, length: int, length_offset: int) -> None:
        """Mask a variable-length UID using the length byte at length_offset."""
        if length >= length_offset + 1:
            uid_len = faked[length_offset]
            start = length_offset + 1
            for i in range(start, start + uid_len):
                if i < len(faked) - 1:
                    faked[i] = FAKE_UID_BYTE

    @staticmethod
    def _is_pin_based_history(opcode: int) -> bool:
        """Check if an opcode is a history event containing a PIN."""
        return opcode in (
            BoksHistoryEvent.CODE_BLE_VALID,
            BoksHistoryEvent.CODE_KEY_VALID,
            BoksHistoryEvent.CODE_BLE_INVALID,
            BoksHistoryEvent.CODE_KEY_INVALID
        )

    @staticmethod
    def _anonymize_nfc_payload(faked: bytearray, opcode: int) -> bool:
        """Anonymize UID in NFC-related payloads."""
        # 0xA1: [Age(3)] [Type(1)] [UID_Len(1)] [UID(NB)]
        # 0xC5: [UID_Len(1)] [UID(NB)]
        offset = 6 if opcode == BoksHistoryEvent.NFC_OPENING else 3
        if len(faked) > offset:
            uid_len = faked[offset - 1]
            for i in range(offset, offset + uid_len):
                if i < len(faked) - 1:
                    faked[i] = FAKE_UID_BYTE
            return True
        return False

    @staticmethod
    def get_packet_log_info(data: Optional[bytearray], anonymize: bool = True) -> dict[str, str]:
        """Get formatted hex strings and suffix for logging a packet."""
        if data is None:
            return {"payload": "", "raw": "None", "suffix": ""}
            
        faked_data = BoksAnonymizer.anonymize_packet(data, anonymize)
        
        return {
            "payload": faked_data[2:-1].hex() if len(faked_data) > 3 else "",
            "raw": faked_data.hex(),
            "suffix": " (ANONYMIZED)" if anonymize else ""
        }