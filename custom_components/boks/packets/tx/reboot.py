"""TX Packet: Reboot."""
from ..base import BoksTXPacket
from ...ble.const import BoksCommandOpcode

class RebootPacket(BoksTXPacket):
    """Command to trigger a software reboot."""

    def __init__(self):
        super().__init__(BoksCommandOpcode.REBOOT)

    def to_bytes(self) -> bytearray:
        return self._build_framed_packet(b"")
