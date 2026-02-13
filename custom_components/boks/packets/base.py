"""Base packet definitions for Boks."""
from abc import ABC, abstractmethod
from typing import Any

from ..ble.const import BoksCommandOpcode, BoksHistoryEvent, BoksNotificationOpcode


class BoksPacket(ABC):
    """Base class for all Boks packets."""

    def __init__(self, opcode: int):
        """Initialize the packet."""
        self.opcode = opcode

    def get_opcode_name(self) -> str:
        """Return a readable name for the opcode."""
        for enum_class in [BoksCommandOpcode, BoksNotificationOpcode, BoksHistoryEvent]:
            try:
                return enum_class(self.opcode).name
            except ValueError:
                continue
        return "UNKNOWN"

    @staticmethod
    def calculate_checksum(data: bytearray) -> int:
        """Calculate 8-bit checksum."""
        return sum(data) & 0xFF

    def verify_checksum(self) -> bool:
        """Verify the checksum of the packet."""
        data = self.to_bytes()
        if len(data) < 1:
            return False
        return BoksPacket.calculate_checksum(data[:-1]) == data[-1]

    @abstractmethod
    def to_bytes(self) -> bytearray:
        """Serialize packet to bytes."""

    @abstractmethod
    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        """Return a dictionary for logging purposes."""

class BoksTXPacket(BoksPacket):
    """Base class for outgoing command packets."""

    def _build_framed_packet(self, payload: bytes) -> bytearray:
        """Framework for building TX packets [Opcode][Len][Payload][CRC]."""
        packet = bytearray()
        packet.append(self.opcode)
        packet.append(len(payload))
        packet.extend(payload)
        packet.append(self.calculate_checksum(packet))
        return packet

    @abstractmethod
    def to_bytes(self) -> bytearray:
        """Serialize packet to bytes."""

    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        """Default logging for TX packets."""
        raw_bytes = self.to_bytes()
        return {
            "payload": raw_bytes[2:-1].hex() if len(raw_bytes) > 3 else "",
            "raw": raw_bytes.hex(),
            "suffix": ""
        }

class BoksRXPacket(BoksPacket):
    """Base class for incoming notification/log packets."""

    # Can be a single int or a list of opcodes
    OPCODES: int | list[int] | None = None

    def __init__(self, opcode: int, raw_data: bytearray):
        """Initialize with raw data."""
        super().__init__(opcode)
        self.raw_data = raw_data
        # Extract payload: [Opcode][Len][Payload...][CRC]
        self.payload = raw_data[2:-1] if len(raw_data) > 3 else bytearray()

    def to_bytes(self) -> bytearray:
        """Return raw bytes."""
        return self.raw_data

    def to_log_dict(self, anonymize: bool = True) -> dict[str, str]:
        """Default logging for RX packets."""
        return {
            "payload": self.payload.hex(),
            "raw": self.raw_data.hex(),
            "suffix": ""
        }

    @property
    def event_type(self) -> str:
        """Return the event type string for this packet."""
        from ..ble.const import LOG_EVENT_TYPES
        return LOG_EVENT_TYPES.get(self.opcode, "unknown")

    @property
    def extra_data(self) -> dict[str, Any]:
        """Return additional parsed data for HA events."""
        return {}

class BoksHistoryLogPacket(BoksRXPacket):
    """Base class for history log entries (usually starts with 3 bytes Age)."""

    def __init__(self, opcode: int, raw_data: bytearray):
        """Initialize and parse common Age field."""
        super().__init__(opcode, raw_data)
        self.age = int.from_bytes(self.payload[0:3], 'big') if len(self.payload) >= 3 else 0
        # Specific logs will parse the rest of the payload starting at index 3
        self.log_payload = self.payload[3:] if len(self.payload) > 3 else bytearray()

    def _get_base_log_payload(self) -> str:
        """Helper to get common log payload string."""
        return f"Age={self.age}s"
