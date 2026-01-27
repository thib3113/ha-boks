"""TX Packet: Reboot."""
from ...ble.const import BoksCommandOpcode
from ..base import BoksTXPacket


class RebootPacket(BoksTXPacket):
    """Command to trigger a software reboot."""

    def __init__(self):
        super().__init__(BoksCommandOpcode.REBOOT)

    def to_bytes(self) -> bytearray:
        return self._build_framed_packet(b"")
