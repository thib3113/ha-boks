"""Test for DoorOpenedPacket."""
import pytest
from custom_components.boks.packets.rx.door_opened import DoorOpenedPacket
from custom_components.boks.ble.const import BoksHistoryEvent

def test_parse_door_opened(mock_time, packet_builder):
    """Test parsing DoorOpenedPacket."""
    # Payload: Age(3)
    payload = bytes.fromhex("0000FF")
    data = packet_builder(BoksHistoryEvent.DOOR_OPENED, payload)

    packet = DoorOpenedPacket(data)

    assert packet.opcode == BoksHistoryEvent.DOOR_OPENED
    assert packet.event_type == "door_opened"