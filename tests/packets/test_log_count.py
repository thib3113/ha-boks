"""Test for LogCountPacket."""
import pytest
from custom_components.boks.packets.rx.log_count import LogCountPacket
from custom_components.boks.ble.const import BoksHistoryEvent, BoksNotificationOpcode

def test_parse_log_count(mock_time, packet_builder):
    """Test parsing LogCountPacket."""
    # TODO: Define valid payload
    payload = bytes.fromhex("000000")
    # Use opcode from class if available, or placeholder
    opcode = BoksNotificationOpcode.NOTIFY_LOGS_COUNT

    data = packet_builder(opcode, payload)

    # Check if class allows instantiation with just data or opcode+data
    try:
        packet = LogCountPacket(data)
    except TypeError:
        packet = LogCountPacket(opcode, data)

    assert packet.opcode == opcode