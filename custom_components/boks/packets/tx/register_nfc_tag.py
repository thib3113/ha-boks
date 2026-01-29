"""TX Packet: Register NFC Tag."""
from ...ble.const import BoksCommandOpcode
from ...logic.anonymizer import BoksAnonymizer
from ..base import BoksTXPacket


class RegisterNfcTagPacket(BoksTXPacket):
    """Command to register an NFC tag in the Boks whitelist."""

    def __init__(self, config_key: str, uid: str):
        """Initialize with config key and UID (hex string)."""
        super().__init__(BoksCommandOpcode.REGISTER_NFC_TAG)
        self.config_key = config_key
        # Normalize UID
        self.uid = uid.replace(":", "").replace(" ", "").upper()
        try:
            self.uid_bytes = bytes.fromhex(self.uid)
        except ValueError:
            self.uid_bytes = b""

    def to_bytes(self) -> bytearray:
        """Build payload: [ConfigKey(8)][UIDLen(1)][UID(NB)]."""
        payload = bytearray(self.config_key.encode('ascii'))
        payload.append(len(self.uid_bytes))
        payload.extend(self.uid_bytes)
        return self._build_framed_packet(payload)

    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        """Log info with masked key and UID."""
        log_key = BoksAnonymizer.anonymize_key(self.config_key, anonymize)
        log_uid = BoksAnonymizer.anonymize_uid(self.uid, anonymize)

        return {
            "payload": f"Key={log_key}, UID={log_uid}",
            "raw": self.to_bytes().hex(),
            "suffix": " (ANONYMIZED)" if anonymize else ""
        }
