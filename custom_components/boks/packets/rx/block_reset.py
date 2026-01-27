"""RX Packet: Block Reset."""
from ..base import BoksHistoryLogPacket
from ...ble.const import BoksHistoryEvent

class BlockResetPacket(BoksHistoryLogPacket):
    """Log entry for block reset event."""

    OPCODE = BoksHistoryEvent.BLOCK_RESET

    def __init__(self, raw_data: bytearray):
        super().__init__(BoksHistoryEvent.BLOCK_RESET, raw_data)
        self.reset_info = self.log_payload.hex() if self.log_payload else ""

    @property
    def extra_data(self) -> dict:
        return {"reset_info": self.reset_info}

    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        payload = self._get_base_log_payload()
        if self.reset_info:
            payload = f"{payload}, ResetInfo={self.reset_info}"
        return {
            "payload": payload,
            "raw": self.raw_data.hex(),
            "suffix": ""
        }
