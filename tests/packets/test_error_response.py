"""Test for ErrorResponsePacket."""
import pytest
from custom_components.boks.packets.rx.error_response import ErrorResponsePacket
from custom_components.boks.ble.const import BoksHistoryEvent, BoksNotificationOpcode

def test_parse_error_response(mock_time, packet_builder):
    """Test parsing ErrorResponsePacket."""
    # TODO: Define valid payload
    payload = bytes.fromhex("000000")
    # Use opcode from class if available, or placeholder
    opcode = 0x00

    data = packet_builder(opcode, payload)

    # Check if class allows instantiation with just data or opcode+data
    try:
        packet = ErrorResponsePacket(data)
    except TypeError:
        packet = ErrorResponsePacket(opcode, data)

    assert packet.opcode == opcode