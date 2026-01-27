"""TX Packet: Test Battery."""
from ..base import BoksTXPacket
from ...ble.const import BoksCommandOpcode

class BatteryTestPacket(BoksTXPacket):
    """Command to trigger a battery test."""

    def __init__(self):
        super().__init__(BoksCommandOpcode.TEST_BATTERY)

    def to_bytes(self) -> bytearray:
        return self._build_framed_packet(b"")
