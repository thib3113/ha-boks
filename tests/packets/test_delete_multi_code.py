"""Test for DeleteMultiUseCodePacket."""
from custom_components.boks.packets.tx.delete_multi_code import DeleteMultiUseCodePacket
from custom_components.boks.ble.const import BoksCommandOpcode

def test_DeleteMultiUseCodePacket_init():
    """Test initialization of DeleteMultiUseCodePacket."""
    key = "KEY54321"
    pin = "334455"
    packet = DeleteMultiUseCodePacket(key, pin)
    
    assert packet.opcode == BoksCommandOpcode.DELETE_MULTI_USE_CODE
    
    full_packet = packet.to_bytes()
    # Structure: [Opcode][Len][Key(8)][PIN(6)][CRC]
    assert full_packet[0] == BoksCommandOpcode.DELETE_MULTI_USE_CODE
    assert full_packet[1] == 14 # 8+6
    assert full_packet[2:10] == key.encode('ascii')
    assert full_packet[10:16] == pin.encode('ascii')
