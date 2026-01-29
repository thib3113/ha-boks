"""RX Packet: Door Status."""
from ...ble.const import BoksNotificationOpcode
from ..base import BoksRXPacket


class DoorStatusPacket(BoksRXPacket):
    """Notification for current door status (Open/Closed)."""

    OPCODES = [BoksNotificationOpcode.NOTIFY_DOOR_STATUS, BoksNotificationOpcode.ANSWER_DOOR_STATUS]

    def __init__(self, opcode: int, raw_data: bytearray):
        """Initialize and parse status."""
        # Opcode can be NOTIFY_DOOR_STATUS (0x84) or ANSWER_DOOR_STATUS (0x85)
        super().__init__(opcode, raw_data)

        # Payload: [InvertedStatus][LiveStatus]
        self.is_open = False
        if len(self.payload) >= 2:
            self.is_open = self.payload[1] == 1

    @property
    def extra_data(self) -> dict:
        return {"is_open": self.is_open}

    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        """Log info for door status."""
        status_str = "Open" if self.is_open else "Closed"
        return {
            "payload": f"Status={status_str}",
            "raw": self.raw_data.hex(),
            "suffix": ""
        }
