"""Test for CodeKeyValidPacket."""
import pytest
from custom_components.boks.packets.rx.code_key_valid import CodeKeyValidPacket
from custom_components.boks.ble.const import BoksHistoryEvent, BoksNotificationOpcode

def test_parse_code_key_valid(mock_time, packet_builder):
    """Test parsing CodeKeyValidPacket."""
    # TODO: Define valid payload
    payload = bytes.fromhex("000000")
    # Use opcode from class if available, or placeholder
    opcode = BoksHistoryEvent.CODE_KEY_VALID

    data = packet_builder(opcode, payload)

    # Check if class allows instantiation with just data or opcode+data
    try:
        packet = CodeKeyValidPacket(data)
    except TypeError:
        packet = CodeKeyValidPacket(opcode, data)

    assert packet.opcode == opcode