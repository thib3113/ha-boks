"""Test for NfcUnregisterTagPacket."""
from custom_components.boks.packets.tx.nfc_unregister_tag import NfcUnregisterTagPacket
from custom_components.boks.ble.const import BoksCommandOpcode

def test_NfcUnregisterTagPacket_init():
    """Test initialization of NfcUnregisterTagPacket."""
    key = "UNREGKEY"
    uid = "04:A1:B2:C3"
    packet = NfcUnregisterTagPacket(key, uid)
    
    assert packet.opcode == BoksCommandOpcode.UNREGISTER_NFC_TAG
    assert packet.uid == "04A1B2C3"
    
    full_packet = packet.to_bytes()
    # Structure: [Opcode][Len][Key(8)][UIDLen(1)][UID(4)][CRC]
    assert full_packet[0] == BoksCommandOpcode.UNREGISTER_NFC_TAG
    assert full_packet[1] == 13 # 8+1+4
    assert full_packet[2:10] == key.encode('ascii')
    assert full_packet[10] == 4  # Len
    assert full_packet[11:15] == bytes.fromhex("04A1B2C3")

def test_NfcUnregisterTagPacket_invalid_uid():
    """Test with invalid UID."""
    packet = NfcUnregisterTagPacket("KEY12345", "ZZZ")
    assert packet.uid_bytes == b""
    # Structure: [Opcode][Len][Key(8)][UIDLen(1)][CRC]
    full_packet = packet.to_bytes()
    assert full_packet[1] == 9 # 8+1
    assert full_packet[10] == 0  # Length 0
