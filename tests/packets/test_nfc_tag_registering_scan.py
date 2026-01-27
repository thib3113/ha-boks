"""Test for NfcTagRegisteringScanPacket."""
from custom_components.boks.packets.rx.nfc_tag_registering_scan import NfcTagRegisteringScanPacket
from custom_components.boks.ble.const import BoksHistoryEvent

def test_parse_nfc_tag_registering_scan():
    """Test parsing of NfcTagRegisteringScanPacket."""
    opcode = BoksHistoryEvent.NFC_TAG_REGISTERING_SCAN
    age_bytes = (5).to_bytes(3, 'big')
    tag_type = 1
    uid_hex = "AABBCC"
    uid_bytes = bytes.fromhex(uid_hex)
    
    raw_data = bytearray()
    raw_data.append(opcode)
    raw_data.append(len(age_bytes) + 2 + len(uid_bytes))
    raw_data.extend(age_bytes)
    raw_data.append(tag_type)
    raw_data.append(len(uid_bytes))
    raw_data.extend(uid_bytes)
    checksum = sum(raw_data) & 0xFF
    raw_data.append(checksum)
    
    packet = NfcTagRegisteringScanPacket(raw_data)
    
    assert packet.opcode == opcode
    assert packet.age == 5
    assert packet.tag_type == tag_type
    assert packet.uid == uid_hex
    assert packet.verify_checksum()