"""TX Packet: Count Codes."""
from ...ble.const import BoksCommandOpcode
from ..base import BoksTXPacket


class CountCodesPacket(BoksTXPacket):
    """Simple command to request the current code counts."""

    def __init__(self):
        """Initialize."""
        super().__init__(BoksCommandOpcode.COUNT_CODES)

    def to_bytes(self) -> bytearray:
        return self._build_framed_packet(b"")
