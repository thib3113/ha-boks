"""TX Packet: Delete Master Code."""
from ..base import BoksTXPacket
from ...ble.const import BoksCommandOpcode
from ...logic.anonymizer import BoksAnonymizer

class DeleteMasterCodePacket(BoksTXPacket):
    """Command to delete a permanent master code by its index."""

    def __init__(self, config_key: str, index: int):
        """Initialize with config key and index."""
        super().__init__(BoksCommandOpcode.DELETE_MASTER_CODE)
        self.config_key = config_key
        self.index = index

    def to_bytes(self) -> bytearray:
        """Build payload: [ConfigKey(8)][Index(1)]."""
        payload = bytearray(self.config_key.encode('ascii'))
        payload.append(self.index)
        return self._build_framed_packet(payload)

    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        """Log info with masked key."""
        log_key = BoksAnonymizer.anonymize_key(self.config_key, anonymize)
        return {
            "payload": f"Key={log_key}, Index={self.index}",
            "raw": self.to_bytes().hex(),
            "suffix": " (ANONYMIZED)" if anonymize else ""
        }
