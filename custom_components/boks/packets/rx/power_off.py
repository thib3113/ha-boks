"""RX Packet: Power Off."""
from ..base import BoksHistoryLogPacket
from ...ble.const import BoksHistoryEvent

class PowerOffPacket(BoksHistoryLogPacket):
    """Notification for a device power off/reset."""

    OPCODE = BoksHistoryEvent.POWER_OFF

    def __init__(self, raw_data: bytearray):
        super().__init__(BoksHistoryEvent.POWER_OFF, raw_data)
        self.reason_code = self.log_payload[0] if self.log_payload else 0

    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        return {
            "payload": f"ReasonCode={self.reason_code}, {self._get_base_log_payload()}",
            "raw": self.raw_data.hex(),
            "suffix": ""
        }
