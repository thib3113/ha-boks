"""TX Packet: Get Logs Count."""
from ..base import BoksTXPacket
from ...ble.const import BoksCommandOpcode

class GetLogsCountPacket(BoksTXPacket):
    """Simple command to request the number of available logs."""

    def __init__(self):
        """Initialize."""
        super().__init__(BoksCommandOpcode.GET_LOGS_COUNT)

    def to_bytes(self) -> bytearray:
        return self._build_framed_packet(b"")
