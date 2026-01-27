"""RX Packet: Log Count."""
from ...ble.const import BoksNotificationOpcode
from ..base import BoksRXPacket


class LogCountPacket(BoksRXPacket):
    """Notification containing the number of available logs."""

    OPCODE = BoksNotificationOpcode.NOTIFY_LOGS_COUNT

    def __init__(self, raw_data: bytearray):
        """Initialize and parse count."""
        super().__init__(BoksNotificationOpcode.NOTIFY_LOGS_COUNT, raw_data)
        # Payload: [Count_MSB][Count_LSB]
        self.count = 0
        if len(self.payload) >= 2:
            self.count = (self.payload[0] << 8) | self.payload[1]

    @property
    def extra_data(self) -> dict:
        return {"count": self.count}

    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        """Log info for log count."""
        return {
            "payload": f"Count={self.count}",
            "raw": self.raw_data.hex(),
            "suffix": ""
        }
