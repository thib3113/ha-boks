"""Test for EndHistoryPacket."""
import pytest
from custom_components.boks.packets.rx.end_history import EndHistoryPacket
from custom_components.boks.ble.const import BoksHistoryEvent, BoksNotificationOpcode

def test_parse_end_history(mock_time, packet_builder):
    """Test parsing EndHistoryPacket."""
    # TODO: Define valid payload
    payload = bytes.fromhex("000000")
    # Use opcode from class if available, or placeholder
    opcode = BoksHistoryEvent.LOG_END_HISTORY

    data = packet_builder(opcode, payload)

    # Check if class allows instantiation with just data or opcode+data
    try:
        packet = EndHistoryPacket(data)
    except TypeError:
        packet = EndHistoryPacket(opcode, data)

    assert packet.opcode == opcode