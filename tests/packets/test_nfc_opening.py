"""Test for NfcOpeningPacket."""
from custom_components.boks.packets.rx.nfc_opening import NfcOpeningPacket
from custom_components.boks.ble.const import BoksHistoryEvent

def test_parse_nfc_opening():
    """Test parsing of NfcOpeningPacket."""
    opcode = BoksHistoryEvent.NFC_OPENING
    age_bytes = (10).to_bytes(3, 'big')
    tag_type = 2
    uid_hex = "04050607"
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
    
    packet = NfcOpeningPacket(raw_data)
    
    assert packet.opcode == opcode
    assert packet.age == 10
    assert packet.tag_type == tag_type
    assert packet.uid == uid_hex
    assert packet.extra_data["tag_type"] == tag_type
    assert packet.extra_data["tag_uid"] == uid_hex
    assert packet.verify_checksum()
