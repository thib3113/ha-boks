"""Test for DeleteSingleUseCodePacket."""
from custom_components.boks.packets.tx.delete_single_code import DeleteSingleUseCodePacket
from custom_components.boks.ble.const import BoksCommandOpcode

def test_DeleteSingleUseCodePacket_init():
    """Test initialization of DeleteSingleUseCodePacket."""
    key = "KEY00000"
    pin = "998877"
    packet = DeleteSingleUseCodePacket(key, pin)
    
    assert packet.opcode == BoksCommandOpcode.DELETE_SINGLE_USE_CODE
    
    full_packet = packet.to_bytes()
    # Structure: [Opcode][Len][Key(8)][PIN(6)][CRC]
    assert full_packet[0] == BoksCommandOpcode.DELETE_SINGLE_USE_CODE
    assert full_packet[1] == 14 # 8+6
    assert full_packet[2:10] == key.encode('ascii')
    assert full_packet[10:16] == pin.encode('ascii')
