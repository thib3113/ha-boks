"""Test for DoorClosedPacket."""
import pytest
from custom_components.boks.packets.rx.door_closed import DoorClosedPacket
from custom_components.boks.ble.const import BoksHistoryEvent, BoksNotificationOpcode

def test_parse_door_closed(mock_time, packet_builder):
    """Test parsing DoorClosedPacket."""
    # TODO: Define valid payload
    payload = bytes.fromhex("000000")
    # Use opcode from class if available, or placeholder
    opcode = BoksHistoryEvent.DOOR_CLOSED

    data = packet_builder(opcode, payload)

    # Check if class allows instantiation with just data or opcode+data
    try:
        packet = DoorClosedPacket(data)
    except TypeError:
        packet = DoorClosedPacket(opcode, data)

    assert packet.opcode == opcode