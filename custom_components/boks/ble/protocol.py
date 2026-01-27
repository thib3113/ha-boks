"""Boks Protocol definition."""
import logging

_LOGGER = logging.getLogger(__name__)

class BoksProtocol:
    """Handles binary protocol utilities for Boks."""

    @staticmethod
    def calculate_checksum(data: bytearray) -> int:
        """Calculate 8-bit checksum."""
        return sum(data) & 0xFF

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