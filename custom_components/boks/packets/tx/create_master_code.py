"""TX Packet: Create Master Code."""
from ...ble.const import BoksCommandOpcode
from ...logic.anonymizer import BoksAnonymizer
from ..base import BoksTXPacket


class CreateMasterCodePacket(BoksTXPacket):
    """Command to create a permanent master code at a specific index."""

    def __init__(self, config_key: str, pin: str, index: int):
        super().__init__(BoksCommandOpcode.CREATE_MASTER_CODE)
        self.config_key = config_key
        self.pin = pin
        self.index = index

    def to_bytes(self) -> bytearray:
        # Payload: ConfigKey (8) + Index (1) + PIN (6)
        payload = bytearray(self.config_key.encode('ascii'))
        payload.append(self.index)
        payload.extend(self.pin.encode('ascii'))
        return self._build_framed_packet(payload)

    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        log_pin = BoksAnonymizer.anonymize_pin(self.pin, anonymize)
        log_key = BoksAnonymizer.anonymize_key(self.config_key, anonymize)

        return {
            "payload": f"Key={log_key}, Index={self.index}, PIN={log_pin}",
            "raw": self.to_bytes().hex(),
            "suffix": " (ANONYMIZED)" if anonymize else ""
        }
