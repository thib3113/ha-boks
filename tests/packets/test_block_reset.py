"""Test for BlockResetPacket."""
import pytest
from custom_components.boks.packets.rx.block_reset import BlockResetPacket
from custom_components.boks.ble.const import BoksHistoryEvent, BoksNotificationOpcode

def test_parse_block_reset(mock_time, packet_builder):
    """Test parsing BlockResetPacket."""
    # TODO: Define valid payload
    payload = bytes.fromhex("000000")
    # Use opcode from class if available, or placeholder
    opcode = BoksHistoryEvent.BLOCK_RESET

    data = packet_builder(opcode, payload)

    # Check if class allows instantiation with just data or opcode+data
    try:
        packet = BlockResetPacket(data)
    except TypeError:
        packet = BlockResetPacket(opcode, data)

    assert packet.opcode == opcode