"""Test for NfcScanStartPacket."""
from custom_components.boks.packets.tx.nfc_scan_start import NfcScanStartPacket
from custom_components.boks.ble.const import BoksCommandOpcode

def test_NfcScanStartPacket_init():
    """Test initialization of NfcScanStartPacket."""
    key = "SCANKEY1"
    packet = NfcScanStartPacket(key)
    
    assert packet.opcode == BoksCommandOpcode.REGISTER_NFC_TAG_SCAN_START
    
    full_packet = packet.to_bytes()
    # Structure: [Opcode][Len][Key(8)][CRC]
    assert full_packet[0] == BoksCommandOpcode.REGISTER_NFC_TAG_SCAN_START
    assert full_packet[1] == 8
    assert full_packet[2:10] == key.encode('ascii')
