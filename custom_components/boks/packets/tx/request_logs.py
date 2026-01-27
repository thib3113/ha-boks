"""TX Packet: Request Logs."""
from ..base import BoksTXPacket
from ...ble.const import BoksCommandOpcode

class RequestLogsPacket(BoksTXPacket):
    """Simple command to request the log history."""

    def __init__(self):
        """Initialize."""
        super().__init__(BoksCommandOpcode.REQUEST_LOGS)

    def to_bytes(self) -> bytearray:
        return self._build_framed_packet(b"")
