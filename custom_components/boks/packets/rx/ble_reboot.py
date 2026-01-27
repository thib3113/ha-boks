"""RX Packet: BLE Reboot."""
from ..base import BoksHistoryLogPacket
from ...ble.const import BoksHistoryEvent

class BleRebootPacket(BoksHistoryLogPacket):
    """Log entry for BLE reboot event."""

    OPCODE = BoksHistoryEvent.BLE_REBOOT

    def __init__(self, raw_data: bytearray):
        super().__init__(BoksHistoryEvent.BLE_REBOOT, raw_data)

    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        return {
            "payload": self._get_base_log_payload(),
            "raw": self.raw_data.hex(),
            "suffix": ""
        }
