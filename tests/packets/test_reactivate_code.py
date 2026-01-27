"""Test for ReactivateCodePacket."""
from custom_components.boks.packets.tx.reactivate_code import ReactivateCodePacket
from custom_components.boks.ble.const import BoksCommandOpcode

def test_ReactivateCodePacket_init():
    """Test initialization of ReactivateCodePacket."""
    key = "REACTKEY"
    code = "998877"
    packet = ReactivateCodePacket(key, code)
    
    assert packet.opcode == BoksCommandOpcode.REACTIVATE_CODE
    
    full_packet = packet.to_bytes()
    # Structure: [Opcode][Len][Key(8)][Code(6)][CRC]
    assert full_packet[0] == BoksCommandOpcode.REACTIVATE_CODE
    assert full_packet[1] == 14 # 8+6
    assert full_packet[2:10] == key.encode('ascii')
    assert full_packet[10:16] == code.encode('ascii')
