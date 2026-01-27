"""RX Packet: End History."""
from ...ble.const import BoksHistoryEvent
from ..base import BoksHistoryLogPacket


class EndHistoryPacket(BoksHistoryLogPacket):
    """Log entry for end of history event."""

    OPCODE = BoksHistoryEvent.LOG_END_HISTORY

    def __init__(self, raw_data: bytearray):
        super().__init__(BoksHistoryEvent.LOG_END_HISTORY, raw_data)

    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        return {
            "payload": self._get_base_log_payload(),
            "raw": self.raw_data.hex(),
            "suffix": ""
        }
