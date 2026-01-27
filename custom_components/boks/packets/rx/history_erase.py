"""RX Packet: History Erase."""
from ...ble.const import BoksHistoryEvent
from ..base import BoksHistoryLogPacket


class HistoryErasePacket(BoksHistoryLogPacket):
    """Log entry for history erase event."""

    OPCODE = BoksHistoryEvent.HISTORY_ERASE

    def __init__(self, raw_data: bytearray):
        super().__init__(BoksHistoryEvent.HISTORY_ERASE, raw_data)

    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        return {
            "payload": self._get_base_log_payload(),
            "raw": self.raw_data.hex(),
            "suffix": ""
        }
