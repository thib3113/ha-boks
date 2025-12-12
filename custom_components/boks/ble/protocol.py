"""Boks Protocol definition."""
import logging
from typing import Optional

from .log_entry import BoksLogEntry

_LOGGER = logging.getLogger(__name__)

class BoksProtocol:
    """Handles binary protocol serialization and deserialization for Boks."""

    @staticmethod
    def calculate_checksum(data: bytearray) -> int:
        """Calculate 8-bit checksum."""
        return sum(data) & 0xFF

    @staticmethod
    def build_packet(opcode: int, payload: bytes = b"") -> bytearray:
        """Build a command packet with checksum."""
        packet = bytearray()
        packet.append(opcode)
        packet.append(len(payload))
        packet.extend(payload)
        packet.append(BoksProtocol.calculate_checksum(packet))
        return packet

    @staticmethod
    def verify_checksum(data: bytearray) -> bool:
        """Verify checksum of received data."""
        if len(data) < 1:
            return False
        payload_part = data[:-1]
        checksum = data[-1]
        return BoksProtocol.calculate_checksum(payload_part) == checksum

    @staticmethod
    def parse_door_status(data: bytearray) -> bool | None:
        """
        Parse door status notification.
        Returns True if Open, False if Closed, None if invalid.
        """
        # Opcode + Len + 2 bytes payload + Checksum = 5 bytes minimum usually
        if len(data) >= 4:
            # Payload is 2 bytes: [Inverted Status, Live Status]
            # Index 3 is Live Status (0=Closed, 1=Open)
            raw_state = data[3]
            return raw_state == 1
        return None

    @staticmethod
    def parse_code_counts(payload: bytes) -> dict:
        """Parse code counts response payload."""
        if len(payload) >= 4:
            master_count = int.from_bytes(payload[0:2], 'big')
            single_use_count = int.from_bytes(payload[2:4], 'big')
            return {
                "master": master_count,
                "single_use": single_use_count,
            }
        return {}

    @staticmethod
    def parse_logs_count(data: bytearray) -> int | None:
        """Parse logs count notification."""
        if len(data) >= 4:
            # Payload is 2 bytes: [LogCount_MSB][LogCount_LSB]
            return (data[2] << 8) | data[3]
        return None

    @staticmethod
    def parse_battery_stats(payload: bytes) -> dict | None:
        """
        Parse battery stats custom characteristic payload.
        Returns None if payload is invalid (e.g. all FF).
        """
        if not payload:
            return None

        # Check for invalid payload (all FF)
        if all(b == 255 for b in payload):
             return None

        stats = {"format": "unknown", "temperature": None}

        if len(payload) == 6:
            stats["format"] = "measures-first-min-mean-max-last"
            raw_temp = payload[5]
            temperature = raw_temp - 25 if raw_temp != 255 else None

            stats.update({
                "level_first": payload[0],
                "level_min": payload[1],
                "level_mean": payload[2],
                "level_max": payload[3],
                "level_last": payload[4],
                "temperature": temperature
            })
            return stats

        elif len(payload) == 4:
            stats["format"] = "measures-t1-t5-t10"
            raw_temp = payload[3]
            temperature = raw_temp - 25 if raw_temp != 255 else None

            stats.update({
                "level_t1": payload[0],
                "level_t5": payload[1] if payload[1] != 255 else None,
                "level_t10": payload[2] if payload[2] != 255 else None,
                "temperature": temperature
            })
            return stats

        return None

    @staticmethod
    def parse_log_entry(opcode: int, data: bytearray) -> Optional[BoksLogEntry]:
        """Parse a log entry from raw data."""
        try:
            payload = data[2:-1] if data and len(data) > 3 else bytearray()
            return BoksLogEntry.from_raw(opcode, payload)
        except Exception as e:
            _LOGGER.warning(f"Protocol error parsing log entry 0x{opcode:02X}: {e}")
            return None
