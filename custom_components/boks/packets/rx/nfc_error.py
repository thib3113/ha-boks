"""RX Packet: NFC Register Errors."""
from ..base import BoksRXPacket
from ...ble.const import BoksNotificationOpcode

class NfcErrorPacket(BoksRXPacket):
    """Notification for NFC specific errors during registration."""

    OPCODES = [
        BoksNotificationOpcode.ERROR_NFC_TAG_ALREADY_EXISTS_REGISTER
    ]

    def __init__(self, opcode: int, raw_data: bytearray):
        """Initialize."""
        super().__init__(opcode, raw_data)

    @property
    def error_type(self) -> str:
        """Return a string identifying the error type."""
        if self.opcode == BoksNotificationOpcode.ERROR_NFC_TAG_ALREADY_EXISTS_REGISTER:
            return "TAG_ALREADY_EXISTS_REGISTER"
        return "UNKNOWN_NFC_ERROR"

    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        """Log info for NFC error."""
        return {
            "payload": f"Error={self.error_type}",
            "raw": self.raw_data.hex(),
            "suffix": ""
        }
