"""Test for HistoryErasePacket."""
import pytest
from custom_components.boks.packets.rx.history_erase import HistoryErasePacket
from custom_components.boks.ble.const import BoksHistoryEvent, BoksNotificationOpcode

def test_parse_history_erase(mock_time, packet_builder):
    """Test parsing HistoryErasePacket."""
    # TODO: Define valid payload
    payload = bytes.fromhex("000000")
    # Use opcode from class if available, or placeholder
    opcode = BoksHistoryEvent.HISTORY_ERASE

    data = packet_builder(opcode, payload)

    # Check if class allows instantiation with just data or opcode+data
    try:
        packet = HistoryErasePacket(data)
    except TypeError:
        packet = HistoryErasePacket(opcode, data)

    assert packet.opcode == opcode