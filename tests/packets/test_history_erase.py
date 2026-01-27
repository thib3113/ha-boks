"""Test for HistoryErasePacket."""
from custom_components.boks.packets.rx.history_erase import HistoryErasePacket
from custom_components.boks.ble.const import BoksHistoryEvent

def test_parse_history_erase():
    """Test parsing of HistoryErasePacket."""
    opcode = BoksHistoryEvent.HISTORY_ERASE
    age_bytes = (1).to_bytes(3, 'big')
    
    raw_data = bytearray()
    raw_data.append(opcode)
    raw_data.append(len(age_bytes))
    raw_data.extend(age_bytes)
    checksum = sum(raw_data) & 0xFF
    raw_data.append(checksum)
    
    packet = HistoryErasePacket(raw_data)
    
    assert packet.opcode == opcode
    assert packet.age == 1
    assert packet.verify_checksum()
