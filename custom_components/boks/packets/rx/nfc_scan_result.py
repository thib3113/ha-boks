"""RX Packet: NFC Scan Result."""
from typing import Optional

from ..base import BoksRXPacket
from ...ble.const import BoksNotificationOpcode
from ...logic.anonymizer import BoksAnonymizer


class NfcScanResultPacket(BoksRXPacket):
    """Real-time notification when a tag is found or an error occurs during scan."""

    OPCODE = [
        BoksNotificationOpcode.NOTIFY_NFC_TAG_FOUND,
        BoksNotificationOpcode.ERROR_NFC_TAG_ALREADY_EXISTS_SCAN,
        BoksNotificationOpcode.ERROR_NFC_SCAN_TIMEOUT
    ]

    def __init__(self, opcode: int, raw_data: bytearray):
        super().__init__(opcode, raw_data)
        # Payload for 0xC5/0xC6: [UID_Len(1)] [UID(NB)]
        # Payload for 0xC7: empty
        self.uid: Optional[str] = None
        if self.opcode in (BoksNotificationOpcode.NOTIFY_NFC_TAG_FOUND, BoksNotificationOpcode.ERROR_NFC_TAG_ALREADY_EXISTS_SCAN):
            uid_len = self.payload[0] if len(self.payload) >= 1 else 0
            if uid_len > 0 and len(self.payload) >= 1 + uid_len:
                self.uid = self.payload[1:1+uid_len].hex().upper()

    @property
    def status(self) -> str:
        """Return the status of the scan."""
        if self.opcode == BoksNotificationOpcode.NOTIFY_NFC_TAG_FOUND:
            return "found"
        if self.opcode == BoksNotificationOpcode.ERROR_NFC_TAG_ALREADY_EXISTS_SCAN:
            return "already_exists"
        if self.opcode == BoksNotificationOpcode.ERROR_NFC_SCAN_TIMEOUT:
            return "timeout"
        return "unknown"

    @property
    def extra_data(self) -> dict:
        return {"tag_uid": self.uid, "status": self.status}

    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        display_uid = BoksAnonymizer.anonymize_uid(self.uid, anonymize) if self.uid else "None"
        return {
            "payload": f"Status={self.status}, UID={display_uid}",
            "raw": self.raw_data.hex(),
            "suffix": " (ANONYMIZED)" if anonymize and self.uid else ""
        }
