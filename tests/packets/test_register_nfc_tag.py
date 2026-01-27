"""Test for RegisterNfcTagPacket."""
from custom_components.boks.packets.tx.register_nfc_tag import RegisterNfcTagPacket
from custom_components.boks.ble.const import BoksCommandOpcode

def test_RegisterNfcTagPacket_init():
    """Test initialization of RegisterNfcTagPacket."""
    key = "REGKEY01"
    uid = "04:05:06:07"
    packet = RegisterNfcTagPacket(key, uid)
    
    assert packet.opcode == BoksCommandOpcode.REGISTER_NFC_TAG
    assert packet.uid == "04050607"
    
    full_packet = packet.to_bytes()
    # Structure: [Opcode][Len][Key(8)][UIDLen(1)][UID(4)][CRC]
    assert full_packet[0] == BoksCommandOpcode.REGISTER_NFC_TAG
    assert full_packet[1] == 13 # 8+1+4
    assert full_packet[2:10] == key.encode('ascii')
    assert full_packet[10] == 4  # Len
    assert full_packet[11:15] == bytes.fromhex("04050607")
