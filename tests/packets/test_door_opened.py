"""Test for DoorOpenedPacket."""
from custom_components.boks.packets.rx.door_opened import DoorOpenedPacket
from custom_components.boks.ble.const import BoksHistoryEvent

def test_parse_door_opened():
    """Test parsing of DoorOpenedPacket."""
    opcode = BoksHistoryEvent.DOOR_OPENED
    age_bytes = (55).to_bytes(3, 'big')
    
    raw_data = bytearray()
    raw_data.append(opcode)
    raw_data.append(len(age_bytes))
    raw_data.extend(age_bytes)
    checksum = sum(raw_data) & 0xFF
    raw_data.append(checksum)
    
    packet = DoorOpenedPacket(raw_data)
    
    assert packet.opcode == opcode
    assert packet.age == 55
    assert packet.verify_checksum()
