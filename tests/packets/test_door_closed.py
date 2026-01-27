"""Test for DoorClosedPacket."""
from custom_components.boks.packets.rx.door_closed import DoorClosedPacket
from custom_components.boks.ble.const import BoksHistoryEvent

def test_parse_door_closed():
    """Test parsing of DoorClosedPacket."""
    opcode = BoksHistoryEvent.DOOR_CLOSED
    age_bytes = (50).to_bytes(3, 'big')
    
    raw_data = bytearray()
    raw_data.append(opcode)
    raw_data.append(len(age_bytes))
    raw_data.extend(age_bytes)
    checksum = sum(raw_data) & 0xFF
    raw_data.append(checksum)
    
    packet = DoorClosedPacket(raw_data)
    
    assert packet.opcode == opcode
    assert packet.age == 50
    assert packet.verify_checksum()
