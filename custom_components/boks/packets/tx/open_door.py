"""TX Packet: Open Door."""
from ...ble.const import BoksCommandOpcode
from ...logic.anonymizer import BoksAnonymizer
from ..base import BoksTXPacket


class OpenDoorPacket(BoksTXPacket):
    """Command to open the door with an optional PIN."""

    def __init__(self, pin: str = ""):
        super().__init__(BoksCommandOpcode.OPEN_DOOR)
        self.pin = pin

    def to_bytes(self) -> bytearray:
        payload = self.pin.encode('ascii') if self.pin else b""
        return self._build_framed_packet(payload)

    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        log_pin = BoksAnonymizer.anonymize_pin(self.pin, anonymize)
        raw_bytes = self.to_bytes()

        return {
            "payload": log_pin or "",
            "raw": raw_bytes.hex(),
            "suffix": " (ANONYMIZED)" if anonymize and self.pin else ""
        }
