"""RX Packet: Valid BLE Code."""
from ...ble.const import BoksHistoryEvent
from ...logic.anonymizer import BoksAnonymizer
from ..base import BoksHistoryLogPacket


class CodeBleValidPacket(BoksHistoryLogPacket):
    """Log entry for a valid BLE code opening."""

    OPCODE = BoksHistoryEvent.CODE_BLE_VALID

    def __init__(self, raw_data: bytearray):
        super().__init__(BoksHistoryEvent.CODE_BLE_VALID, raw_data)
        self.pin = self.log_payload[0:6].decode('ascii', errors='ignore') if len(self.log_payload) >= 6 else ""

    @property
    def extra_data(self) -> dict:
        return {"code": self.pin}

    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        log_pin = BoksAnonymizer.anonymize_pin(self.pin, anonymize)
        return {
            "payload": f"PIN={log_pin}, {self._get_base_log_payload()}",
            "raw": self.raw_data.hex(),
            "suffix": " (ANONYMIZED)" if anonymize else ""
        }
