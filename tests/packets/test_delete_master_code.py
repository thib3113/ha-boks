"""Test for DeleteMasterCodePacket."""
from custom_components.boks.packets.tx.delete_master_code import DeleteMasterCodePacket
from custom_components.boks.ble.const import BoksCommandOpcode

def test_DeleteMasterCodePacket_init():
    """Test initialization of DeleteMasterCodePacket."""
    key = "KEY12345"
    index = 2
    packet = DeleteMasterCodePacket(key, index)
    
    assert packet.opcode == BoksCommandOpcode.DELETE_MASTER_CODE
    
    full_packet = packet.to_bytes()
    # Structure: [Opcode][Len][Key(8)][Index(1)][CRC]
    assert full_packet[0] == BoksCommandOpcode.DELETE_MASTER_CODE
    assert full_packet[1] == 9 # 8+1
    assert full_packet[2:10] == key.encode('ascii')
    assert full_packet[10] == index
