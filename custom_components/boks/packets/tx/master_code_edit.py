"""TX Packet: Master Code Edit."""
from ..base import BoksTXPacket
from ...ble.const import BoksCommandOpcode
from ...logic.anonymizer import BoksAnonymizer

class MasterCodeEditPacket(BoksTXPacket):
    """Command to edit an existing master code."""

    def __init__(self, config_key: str, code_id: int, new_code: str):
        super().__init__(BoksCommandOpcode.MASTER_CODE_EDIT)
        self.config_key = config_key
        self.code_id = code_id
        self.new_code = new_code

    def to_bytes(self) -> bytearray:
        # Payload: [ConfigKey(8)][CodeID(1)][NewCode(NB)]
        payload = bytearray(self.config_key.encode('ascii'))
        payload.append(self.code_id)
        payload.extend(self.new_code.encode('ascii'))
        return self._build_framed_packet(payload)

    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        log_key = BoksAnonymizer.anonymize_key(self.config_key, anonymize)
        log_code = BoksAnonymizer.anonymize_pin(self.new_code, anonymize)
        return {
            "payload": f"Key={log_key}, ID={self.code_id}, NewCode={log_code}",
            "raw": self.to_bytes().hex(),
            "suffix": " (ANONYMIZED)" if anonymize else ""
        }
