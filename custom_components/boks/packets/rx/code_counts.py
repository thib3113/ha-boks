"""RX Packet: Code Counts."""
from ..base import BoksRXPacket
from ...ble.const import BoksNotificationOpcode

class CodeCountsPacket(BoksRXPacket):
    """Notification containing current code counts."""

    OPCODES = BoksNotificationOpcode.NOTIFY_CODES_COUNT

    def __init__(self, raw_data: bytearray):
        """Initialize and parse counts."""
        super().__init__(BoksNotificationOpcode.NOTIFY_CODES_COUNT, raw_data)
        # Payload: [MasterCount_MSB][MasterCount_LSB][SingleUseCount_MSB][SingleUseCount_LSB]
        self.master_count = 0
        self.single_use_count = 0
        
        if len(self.payload) >= 4:
            self.master_count = int.from_bytes(self.payload[0:2], 'big')
            self.single_use_count = int.from_bytes(self.payload[2:4], 'big')

    @property
    def extra_data(self) -> dict:
        return {"master": self.master_count, "single_use": self.single_use_count}

    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        """Log info for code counts."""
        return {
            "payload": f"Master={self.master_count}, SingleUse={self.single_use_count}",
            "raw": self.raw_data.hex(),
            "suffix": ""
        }
