"""Test for ErrorLogPacket."""
import pytest
from custom_components.boks.packets.rx.error_log import ErrorLogPacket
from custom_components.boks.ble.const import BoksHistoryEvent

def test_parse_error_log(mock_time, packet_builder):
    """Test parsing ErrorLogPacket."""
    # Payload: Age(3) + ErrorCode(1)
    payload = bytes.fromhex("00000ABC")
    data = packet_builder(BoksHistoryEvent.ERROR, payload)

    packet = ErrorLogPacket(data)

    assert packet.opcode == BoksHistoryEvent.ERROR
    assert packet.error_code == 0xBC
    assert packet.extra_data["error_code"] == 0xBC
    assert packet.extra_data["error_description"] == "diagnostic_error_bc"