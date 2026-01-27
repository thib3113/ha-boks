"""Test for DoorStatusPacket."""
from custom_components.boks.packets.rx.door_status import DoorStatusPacket
from custom_components.boks.ble.const import BoksNotificationOpcode

def test_parse_door_status():
    """Test parsing of DoorStatusPacket."""
    # Test NOTIFY
    opcode = BoksNotificationOpcode.NOTIFY_DOOR_STATUS
    payload = bytes([0xFE, 0x01]) # Status=1 (Open)
    
    raw_data = bytearray()
    raw_data.append(opcode)
    raw_data.append(len(payload))
    raw_data.extend(payload)
    checksum = sum(raw_data) & 0xFF
    raw_data.append(checksum)
    
    packet = DoorStatusPacket(opcode, raw_data)
    
    assert packet.opcode == opcode
    assert packet.is_open is True
    assert packet.verify_checksum()

    # Test ANSWER (Closed)
    opcode = BoksNotificationOpcode.ANSWER_DOOR_STATUS
    payload = bytes([0xFF, 0x00]) # Status=0 (Closed)
    
    raw_data = bytearray()
    raw_data.append(opcode)
    raw_data.append(len(payload))
    raw_data.extend(payload)
    checksum = sum(raw_data) & 0xFF
    raw_data.append(checksum)
    
    packet = DoorStatusPacket(opcode, raw_data)
    
    assert packet.opcode == opcode
    assert packet.is_open is False
    assert packet.verify_checksum()
