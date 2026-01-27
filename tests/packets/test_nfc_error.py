"""Test for NfcErrorPacket."""
from custom_components.boks.packets.rx.nfc_error import NfcErrorPacket
from custom_components.boks.ble.const import BoksNotificationOpcode

def test_parse_nfc_error():
    """Test parsing of NfcErrorPacket."""
    opcode = BoksNotificationOpcode.ERROR_NFC_TAG_ALREADY_EXISTS_REGISTER
    raw_data = bytearray([opcode, 0x00, opcode]) # No payload
    
    packet = NfcErrorPacket(opcode, raw_data)
    
    assert packet.opcode == opcode
    assert packet.error_type == "TAG_ALREADY_EXISTS_REGISTER"
    assert packet.verify_checksum()
