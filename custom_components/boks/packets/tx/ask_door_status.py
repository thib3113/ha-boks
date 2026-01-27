"""TX Packet: Ask Door Status."""
from ...ble.const import BoksCommandOpcode
from ..base import BoksTXPacket


class AskDoorStatusPacket(BoksTXPacket):
    """Simple command to request the current door status."""

    def __init__(self):
        """Initialize."""
        super().__init__(BoksCommandOpcode.ASK_DOOR_STATUS)

    def to_bytes(self) -> bytearray:
        return self._build_framed_packet(b"")
