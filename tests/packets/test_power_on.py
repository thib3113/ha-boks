"""Test for PowerOnPacket."""
import pytest
from custom_components.boks.packets.rx.power_on import PowerOnPacket
from custom_components.boks.ble.const import BoksHistoryEvent, BoksNotificationOpcode

def test_parse_power_on(mock_time, packet_builder):
    """Test parsing PowerOnPacket."""
    # TODO: Define valid payload
    payload = bytes.fromhex("000000")
    # Use opcode from class if available, or placeholder
    opcode = BoksHistoryEvent.POWER_ON

    data = packet_builder(opcode, payload)

    # Check if class allows instantiation with just data or opcode+data
    try:
        packet = PowerOnPacket(data)
    except TypeError:
        packet = PowerOnPacket(opcode, data)

    assert packet.opcode == opcode