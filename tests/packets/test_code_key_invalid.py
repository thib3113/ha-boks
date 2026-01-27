"""Test for CodeKeyInvalidPacket."""
import pytest
from custom_components.boks.packets.rx.code_key_invalid import CodeKeyInvalidPacket
from custom_components.boks.ble.const import BoksHistoryEvent, BoksNotificationOpcode

def test_parse_code_key_invalid(mock_time, packet_builder):
    """Test parsing CodeKeyInvalidPacket."""
    # TODO: Define valid payload
    payload = bytes.fromhex("000000") 
    # Use opcode from class if available, or placeholder
    opcode = BoksHistoryEvent.CODE_KEY_INVALID
    
    data = packet_builder(opcode, payload)
    
    # Check if class allows instantiation with just data or opcode+data
    try:
        packet = CodeKeyInvalidPacket(data)
    except TypeError:
        packet = CodeKeyInvalidPacket(opcode, data)
    
    assert packet.opcode == opcode