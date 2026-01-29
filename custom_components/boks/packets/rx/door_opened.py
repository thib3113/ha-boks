"""RX Packet: Door Opened."""
from ...ble.const import BoksHistoryEvent
from ..base import BoksHistoryLogPacket


class DoorOpenedPacket(BoksHistoryLogPacket):
    """Log entry for door opened event."""

    OPCODES = BoksHistoryEvent.DOOR_OPENED

    def __init__(self, raw_data: bytearray):
        super().__init__(BoksHistoryEvent.DOOR_OPENED, raw_data)

    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        return {
            "payload": self._get_base_log_payload(),
            "raw": self.raw_data.hex(),
            "suffix": ""
        }
