"""Test for ErrorResponsePacket."""
from custom_components.boks.packets.rx.error_response import ErrorResponsePacket
from custom_components.boks.ble.const import BoksNotificationOpcode

def test_parse_error_response():
    """Test parsing of ErrorResponsePacket."""
    # Test AUTH ERROR
    opcode = BoksNotificationOpcode.ERROR_UNAUTHORIZED
    raw_data = bytearray([opcode, 0x00, opcode]) # Checksum == opcode if payload empty
    
    packet = ErrorResponsePacket(opcode, raw_data)
    
    assert packet.opcode == opcode
    assert packet.error_type == "AUTH_ERROR"
    assert packet.extra_data["error_type"] == "AUTH_ERROR"
    assert packet.verify_checksum()
