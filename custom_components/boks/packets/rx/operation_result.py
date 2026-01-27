"""RX Packet: Operation Result."""
from ..base import BoksRXPacket
from ...ble.const import BoksNotificationOpcode

class OperationResultPacket(BoksRXPacket):
    """Notification for the success or failure of an operation."""

    OPCODE = [BoksNotificationOpcode.CODE_OPERATION_SUCCESS, BoksNotificationOpcode.CODE_OPERATION_ERROR]

    def __init__(self, opcode: int, raw_data: bytearray):
        """Initialize."""
        super().__init__(opcode, raw_data)
        self.success = (opcode == BoksNotificationOpcode.CODE_OPERATION_SUCCESS)

    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        """Log info for operation result."""
        result = "SUCCESS" if self.success else "ERROR"
        return {
            "payload": f"Result={result}",
            "raw": self.raw_data.hex(),
            "suffix": ""
        }
