"""Test for OpenCodeResultPacket."""
import pytest
from custom_components.boks.packets.rx.open_code_result import OpenCodeResultPacket
from custom_components.boks.ble.const import BoksHistoryEvent, BoksNotificationOpcode

def test_parse_open_code_result(mock_time, packet_builder):
    """Test parsing OpenCodeResultPacket."""
    # TODO: Define valid payload
    payload = bytes.fromhex("000000")
    # Use opcode from class if available, or placeholder
    opcode = 0x00

    data = packet_builder(opcode, payload)

    # Check if class allows instantiation with just data or opcode+data
    try:
        packet = OpenCodeResultPacket(data)
    except TypeError:
        packet = OpenCodeResultPacket(opcode, data)

    assert packet.opcode == opcode