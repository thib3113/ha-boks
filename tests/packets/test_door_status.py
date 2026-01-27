"""Test for DoorStatusPacket."""
import pytest
from custom_components.boks.packets.rx.door_status import DoorStatusPacket
from custom_components.boks.ble.const import BoksHistoryEvent, BoksNotificationOpcode

def test_parse_door_status(mock_time, packet_builder):
    """Test parsing DoorStatusPacket."""
    # TODO: Define valid payload
    payload = bytes.fromhex("000000")
    # Use opcode from class if available, or placeholder
    opcode = 0x00

    data = packet_builder(opcode, payload)

    # Check if class allows instantiation with just data or opcode+data
    try:
        packet = DoorStatusPacket(data)
    except TypeError:
        packet = DoorStatusPacket(opcode, data)

    assert packet.opcode == opcode