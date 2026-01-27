"""RX Packet: Key Opening."""
from ..base import BoksHistoryLogPacket
from ...ble.const import BoksHistoryEvent

class KeyOpeningPacket(BoksHistoryLogPacket):
    """Log entry for key opening event."""

    OPCODE = BoksHistoryEvent.KEY_OPENING

    def __init__(self, raw_data: bytearray):
        super().__init__(BoksHistoryEvent.KEY_OPENING, raw_data)

    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        return {
            "payload": self._get_base_log_payload(),
            "raw": self.raw_data.hex(),
            "suffix": ""
        }
