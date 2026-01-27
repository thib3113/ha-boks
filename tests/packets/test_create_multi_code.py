"""Test for CreateMultiUseCodePacket."""
from custom_components.boks.packets.tx.create_multi_code import CreateMultiUseCodePacket
from custom_components.boks.ble.const import BoksCommandOpcode

def test_CreateMultiUseCodePacket_init():
    """Test initialization of CreateMultiUseCodePacket."""
    key = "87654321"
    pin = "654321"
    packet = CreateMultiUseCodePacket(key, pin)
    
    assert packet.opcode == BoksCommandOpcode.CREATE_MULTI_USE_CODE
    
    full_packet = packet.to_bytes()
    # Structure: [Opcode][Len][Key(8)][PIN(6)][CRC]
    assert full_packet[0] == BoksCommandOpcode.CREATE_MULTI_USE_CODE
    assert full_packet[1] == 14 # 8+6
    assert full_packet[2:10] == key.encode('ascii')
    assert full_packet[10:16] == pin.encode('ascii')
