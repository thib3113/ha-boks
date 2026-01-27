"""RX Packet: Diagnostic Error Log."""
from ..base import BoksHistoryLogPacket
from ...ble.const import BoksHistoryEvent

class ErrorLogPacket(BoksHistoryLogPacket):
    """Log entry for a technical/diagnostic error."""

    OPCODE = BoksHistoryEvent.ERROR

    def __init__(self, raw_data: bytearray):
        super().__init__(BoksHistoryEvent.ERROR, raw_data)
        # Payload: [Age(3)] [ErrorCode(1)]
        self.error_code = self.log_payload[0] if self.log_payload else 0

    @property
    def extra_data(self) -> dict:
        # Pass the error key so log_processor can translate it
        from ...ble.const import BoksDiagnosticErrorCode
        try:
            diag_enum = BoksDiagnosticErrorCode(self.error_code)
            # Example: MFRC630_ERROR_BC -> diagnostic_error_bc
            error_key = f"diagnostic_error_{diag_enum.name.split('_')[-1].lower()}"
        except (ValueError, Exception):
            error_key = "diagnostic_error_unknown"
            
        return {"error_code": self.error_code, "error_description": error_key}

    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        return {
            "payload": f"ErrorCode=0x{self.error_code:02X}, {self._get_base_log_payload()}",
            "raw": self.raw_data.hex(),
            "suffix": ""
        }
