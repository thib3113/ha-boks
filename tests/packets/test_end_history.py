"""Test for EndHistoryPacket."""
from custom_components.boks.packets.rx.end_history import EndHistoryPacket
from custom_components.boks.ble.const import BoksHistoryEvent

def test_parse_end_history():
    """Test parsing of EndHistoryPacket."""
    opcode = BoksHistoryEvent.LOG_END_HISTORY
    age_bytes = (0).to_bytes(3, 'big') # Usually age 0 for end marker?
    
    raw_data = bytearray()
    raw_data.append(opcode)
    raw_data.append(len(age_bytes))
    raw_data.extend(age_bytes)
    checksum = sum(raw_data) & 0xFF
    raw_data.append(checksum)
    
    packet = EndHistoryPacket(raw_data)
    
    assert packet.opcode == opcode
    assert packet.verify_checksum()
