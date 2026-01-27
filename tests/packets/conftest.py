import pytest
from unittest.mock import patch

@pytest.fixture
def mock_time():
    with patch("time.time") as mock_time:
        mock_time.return_value = 1700000000.0
        yield mock_time

@pytest.fixture
def packet_builder():
    """Fixture that returns a helper function to build RX packets."""
    def _build_rx_packet(opcode: int, payload: bytes) -> bytearray:
        """Helper to build a valid framed RX packet."""
        packet = bytearray()
        packet.append(opcode)
        packet.append(len(payload))
        packet.extend(payload)
        checksum = sum(packet) & 0xFF
        packet.append(checksum)
        return packet
    return _build_rx_packet
