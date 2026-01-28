"""Anonymization utilities for Boks."""
from typing import Optional, Any

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
    def anonymize_mac(mac: Optional[str], anonymize: bool = True) -> Optional[str]:
        """Mask a MAC address (e.g. AA:BB:CC:DD:EE:FF -> AA:BB:CC:XX:XX:XX) if anonymize is True."""
        if not mac or not anonymize:
            return mac

        parts = mac.split(":")
        if len(parts) != 6:
            # Handle potential other formats or non-MAC strings
            if len(mac) > 8:
                return f"{mac[:8]}..."
            return "***"

        return f"{parts[0]}:{parts[1]}:{parts[2]}:XX:XX:XX"

    @staticmethod
    def anonymize_log_message(message: str, anonymize: bool = True) -> str:
        """Find and mask all MAC addresses in a string if anonymize is True."""
        if not message or not anonymize:
            return message

        import re
        # Pattern for MAC addresses (case insensitive)
        mac_pattern = r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})'

        def replace_mac(match):
            mac = match.group(0)
            return BoksAnonymizer.anonymize_mac(mac, True)

        return re.sub(mac_pattern, replace_mac, message)

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
    def get_scanner_info(device: Any, fallback_rssi: int = None) -> dict[str, Any]:
        """
        Return comprehensive bluetooth diagnostic info as a dictionary.
        Keys: scanner_name, scanner_source, target_name, target_address, rssi
        """
        if device is None:
            return {}

        target_name, target_address = BoksAnonymizer._extract_target_info(device)
        rssi_val = fallback_rssi
        if rssi_val is None:
            if hasattr(device, "advertisement"):
                rssi_val = device.advertisement.rssi
            else:
                rssi_val = getattr(device, "rssi", None)

        scanner_name, scanner_source = BoksAnonymizer._extract_scanner_name_and_source(device)
        
        return {
            "scanner_name": scanner_name,
            "scanner_source": scanner_source,
            "target_name": target_name,
            "target_address": target_address,
            "rssi": rssi_val
        }

    @staticmethod
    def get_scanner_display_name(info: dict[str, Any], anonymize: bool = True) -> str:
        """Return a smart display name for the scanner (deduplicated MAC)."""
        name = info.get("scanner_name", "Unknown")
        source = info.get("scanner_source", "unknown")
        anon_source = BoksAnonymizer.anonymize_mac(source, anonymize)
        
        # Normalize for check: remove potential closing parenthesis and spaces
        clean_name = name.strip().rstrip(')').strip()
        
        if clean_name.lower().endswith(source.lower()):
            # Name already contains MAC, don't duplicate
            return name
        
        return f"{name} ({anon_source})"

    @staticmethod
    def format_scanner_info(device: Any, anonymize: bool = True, fallback_rssi: int = None) -> str:
        """
        Format comprehensive bluetooth diagnostic info.
        Format: [Scanner: Name (MAC)] -> [Target: Name (MAC)] (RSSI: value)
        """
        info = BoksAnonymizer.get_scanner_info(device, fallback_rssi)
        if not info:
            return "None"

        scanner_display = BoksAnonymizer.get_scanner_display_name(info, anonymize)
        target_name = info["target_name"]
        target_address = info["target_address"]
        rssi_val = info["rssi"]

        # Determine RSSI string
        if rssi_val in (None, -127, 0):
            rssi_str = "unknown"
        else:
            rssi_str = f"{rssi_val}dBm"

        anon_target = BoksAnonymizer.anonymize_mac(target_address, anonymize)

        return f"[Scanner: {scanner_display}] -> [Target: {target_name} ({anon_target})] (RSSI: {rssi_str})"

    @staticmethod
    def _extract_target_info(device: Any) -> tuple[str, str]:
        """Extract target name and address from device object."""
        name = getattr(device, "name", "Unknown")
        address = getattr(device, "address", "unknown")
        
        if hasattr(device, "ble_device"):
            name = getattr(device.ble_device, "name", name)
            address = getattr(device.ble_device, "address", address)
        return name, address

    @staticmethod
    def _extract_scanner_name_and_source(device: Any) -> tuple[str, str]:
        """Extract scanner name and source MAC from device object."""
        name = "Unknown"
        source = "unknown"

        if hasattr(device, "scanner"):
            source = getattr(device.scanner, "source", "unknown")
            name = BoksAnonymizer._get_scanner_name_from_object(device.scanner)
        else:
            details = getattr(device, "details", {})
            if isinstance(details, dict):
                source = details.get("source", "unknown")
                name = BoksAnonymizer._get_name_from_details(details)

        # Fallback to details if name is still Unknown
        if name == "Unknown":
             ble_device = getattr(device, "ble_device", device)
             name = BoksAnonymizer._get_name_from_details(getattr(ble_device, "details", {}))
        
        return name, source

    @staticmethod
    def _get_scanner_name_from_object(scanner: Any) -> str:
        """Try to find a name in a scanner object."""
        name = getattr(scanner, "name", None)
        if not name or name == "Unknown":
            connector = getattr(scanner, "connector", None)
            if connector:
                name = getattr(connector, "name", None)
        
        if not name or name == "Unknown":
            name = getattr(scanner, "adapter", None)
            
        return name or "Unknown"

    @staticmethod
    def _get_name_from_details(details: Any) -> str:
        """Extract scanner name from details dictionary."""
        if not isinstance(details, dict):
            return "Unknown"
        return details.get("scanner_name") or \
               details.get("proxy_name") or \
               details.get("adapter_name") or \
               details.get("source_name") or \
               "Unknown"

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
