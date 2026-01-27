"""Test for OpenCodeResultPacket."""
from custom_components.boks.packets.rx.open_code_result import OpenCodeResultPacket
from custom_components.boks.ble.const import BoksNotificationOpcode

def test_parse_open_code_result():
    # Valid
    opcode = BoksNotificationOpcode.VALID_OPEN_CODE
    raw_data = bytearray([opcode, 0x00, opcode])
    packet = OpenCodeResultPacket(opcode, raw_data)
    assert packet.valid is True
    assert packet.verify_checksum()
    
    # Invalid
    opcode = BoksNotificationOpcode.INVALID_OPEN_CODE
    raw_data = bytearray([opcode, 0x00, opcode])
    packet = OpenCodeResultPacket(opcode, raw_data)
    assert packet.valid is False
    assert packet.verify_checksum()
