"""Test for OpenDoorPacket."""
from custom_components.boks.packets.tx.open_door import OpenDoorPacket
from custom_components.boks.ble.const import BoksCommandOpcode

def test_OpenDoorPacket_init():
    """Test initialization of OpenDoorPacket with PIN."""
    pin = "123456"
    packet = OpenDoorPacket(pin)
    
    assert packet.opcode == BoksCommandOpcode.OPEN_DOOR
    assert packet.pin == pin
    
    full_packet = packet.to_bytes()
    # Structure: [Opcode][Len][PIN(6)][CRC]
    assert full_packet[0] == BoksCommandOpcode.OPEN_DOOR
    assert full_packet[1] == 6
    assert full_packet[2:8] == pin.encode('ascii')
