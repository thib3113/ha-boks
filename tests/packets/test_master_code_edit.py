"""Test for MasterCodeEditPacket."""
from custom_components.boks.packets.tx.master_code_edit import MasterCodeEditPacket
from custom_components.boks.ble.const import BoksCommandOpcode

def test_MasterCodeEditPacket_init():
    """Test initialization of MasterCodeEditPacket."""
    key = "KEYEDIT1"
    code_id = 5
    new_code = "667788"
    packet = MasterCodeEditPacket(key, code_id, new_code)
    
    assert packet.opcode == BoksCommandOpcode.MASTER_CODE_EDIT
    
    full_packet = packet.to_bytes()
    # Structure: [Opcode][Len][Key(8)][ID(1)][NewCode(6)][CRC]
    assert full_packet[0] == BoksCommandOpcode.MASTER_CODE_EDIT
    assert full_packet[1] == 15 # 8+1+6
    assert full_packet[2:10] == key.encode('ascii')
    assert full_packet[10] == code_id
    assert full_packet[11:17] == new_code.encode('ascii')
