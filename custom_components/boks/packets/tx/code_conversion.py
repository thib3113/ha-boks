"""TX Packet: Code Conversion."""
from ...ble.const import BoksCommandOpcode
from ...logic.anonymizer import BoksAnonymizer
from ..base import BoksTXPacket


class CodeConversionPacket(BoksTXPacket):
    """Command to convert code type (Single->Multi or Multi->Single)."""

    def __init__(self, opcode: int, config_key: str, code_value: str):
        # Opcode: 0x0A (S->M) or 0x0B (M->S)
        super().__init__(opcode)
        self.config_key = config_key
        self.code_value = code_value

    def to_bytes(self) -> bytearray:
        # Payload: [ConfigKey(8)][CodeValue(NB)]
        payload = bytearray(self.config_key.encode('ascii'))
        payload.extend(self.code_value.encode('ascii'))
        return self._build_framed_packet(payload)

    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        log_key = BoksAnonymizer.anonymize_key(self.config_key, anonymize)
        log_code = BoksAnonymizer.anonymize_pin(self.code_value, anonymize)
        type_str = "S->M" if self.opcode == BoksCommandOpcode.SINGLE_USE_CODE_TO_MULTI else "M->S"
        return {
            "payload": f"Type={type_str}, Key={log_key}, Code={log_code}",
            "raw": self.to_bytes().hex(),
            "suffix": " (ANONYMIZED)" if anonymize else ""
        }
