"""RX Packet: Door Closed."""
from ...ble.const import BoksHistoryEvent
from ..base import BoksHistoryLogPacket


class DoorClosedPacket(BoksHistoryLogPacket):
    """Log entry for door closed event."""

    OPCODES = BoksHistoryEvent.DOOR_CLOSED

    def __init__(self, raw_data: bytearray):
        super().__init__(BoksHistoryEvent.DOOR_CLOSED, raw_data)

    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        return {
            "payload": self._get_base_log_payload(),
            "raw": self.raw_data.hex(),
            "suffix": ""
        }
