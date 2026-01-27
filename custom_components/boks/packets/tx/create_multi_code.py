"""TX Packet: Create Multi Use Code."""
from ...ble.const import BoksCommandOpcode
from ...logic.anonymizer import BoksAnonymizer
from ..base import BoksTXPacket


class CreateMultiUseCodePacket(BoksTXPacket):
    """Command to create a multi-use PIN code."""

    def __init__(self, config_key: str, pin: str):
        super().__init__(BoksCommandOpcode.CREATE_MULTI_USE_CODE)
        self.config_key = config_key
        self.pin = pin

    def to_bytes(self) -> bytearray:
        # Payload: ConfigKey (8) + PIN (6)
        payload = bytearray(self.config_key.encode('ascii'))
        payload.extend(self.pin.encode('ascii'))
        return self._build_framed_packet(payload)

    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        log_pin = BoksAnonymizer.anonymize_pin(self.pin, anonymize)
        log_key = BoksAnonymizer.anonymize_key(self.config_key, anonymize)
        return {
            "payload": f"Key={log_key}, PIN={log_pin}",
            "raw": self.to_bytes().hex(),
            "suffix": " (ANONYMIZED)" if anonymize else ""
        }
