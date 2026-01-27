"""Test for CreateMasterCodePacket."""
from custom_components.boks.packets.tx.create_master_code import CreateMasterCodePacket
from custom_components.boks.ble.const import BoksCommandOpcode

def test_CreateMasterCodePacket_init():
    """Test initialization of CreateMasterCodePacket."""
    key = "12345678"
    pin = "123456"
    index = 1
    packet = CreateMasterCodePacket(key, pin, index)
    
    assert packet.opcode == BoksCommandOpcode.CREATE_MASTER_CODE
    
    full_packet = packet.to_bytes()
    # Structure: [Opcode][Len][Key(8)][Index(1)][PIN(6)][CRC]
    assert full_packet[0] == BoksCommandOpcode.CREATE_MASTER_CODE
    assert full_packet[1] == 15 # 8+1+6
    assert full_packet[2:10] == key.encode('ascii')
    assert full_packet[10] == index
    assert full_packet[11:17] == pin.encode('ascii')
