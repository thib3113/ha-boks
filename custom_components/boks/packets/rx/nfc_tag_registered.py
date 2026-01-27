"""RX Packet: NFC Tag Registered."""
from ...ble.const import BoksNotificationOpcode
from ..base import BoksRXPacket


class NfcTagRegisteredPacket(BoksRXPacket):
    """Notification confirming an NFC tag registration."""

    OPCODE = BoksNotificationOpcode.NOTIFY_NFC_TAG_REGISTERED

    def __init__(self, raw_data: bytearray):
        """Initialize."""
        super().__init__(BoksNotificationOpcode.NOTIFY_NFC_TAG_REGISTERED, raw_data)

    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        """Log info for registration."""
        return {
            "payload": "Tag Registered Successfully",
            "raw": self.raw_data.hex(),
            "suffix": ""
        }
