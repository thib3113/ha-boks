"""Test for NfcTagRegisteredPacket."""
from custom_components.boks.packets.rx.nfc_tag_registered import NfcTagRegisteredPacket
from custom_components.boks.ble.const import BoksNotificationOpcode

def test_parse_nfc_tag_registered():
    """Test parsing of NfcTagRegisteredPacket."""
    opcode = BoksNotificationOpcode.NOTIFY_NFC_TAG_REGISTERED
    raw_data = bytearray([opcode, 0x00, opcode])
    
    packet = NfcTagRegisteredPacket(raw_data)
    
    assert packet.opcode == opcode
    assert packet.verify_checksum()