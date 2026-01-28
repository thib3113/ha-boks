"""RX Packet: Power On."""
from ..base import BoksHistoryLogPacket
from ...ble.const import BoksHistoryEvent

class PowerOnPacket(BoksHistoryLogPacket):
    """Log entry for power on event."""

    OPCODES = BoksHistoryEvent.POWER_ON

    def __init__(self, raw_data: bytearray):
        super().__init__(BoksHistoryEvent.POWER_ON, raw_data)

    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        return {
            "payload": self._get_base_log_payload(),
            "raw": self.raw_data.hex(),
            "suffix": ""
        }
