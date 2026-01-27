"""Test for KeyOpeningPacket."""
from custom_components.boks.packets.rx.key_opening import KeyOpeningPacket
from custom_components.boks.ble.const import BoksHistoryEvent

def test_parse_key_opening():
    """Test parsing of KeyOpeningPacket."""
    opcode = BoksHistoryEvent.KEY_OPENING
    age_bytes = (1000).to_bytes(3, 'big')
    
    raw_data = bytearray()
    raw_data.append(opcode)
    raw_data.append(len(age_bytes))
    raw_data.extend(age_bytes)
    checksum = sum(raw_data) & 0xFF
    raw_data.append(checksum)
    
    packet = KeyOpeningPacket(raw_data)
    
    assert packet.opcode == opcode
    assert packet.age == 1000
    assert packet.verify_checksum()