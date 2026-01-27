"""Test for CreateSingleUseCodePacket."""
from custom_components.boks.packets.tx.create_single_code import CreateSingleUseCodePacket
from custom_components.boks.ble.const import BoksCommandOpcode

def test_CreateSingleUseCodePacket_init():
    """Test initialization of CreateSingleUseCodePacket."""
    key = "ABCDEFGH"
    pin = "112233"
    packet = CreateSingleUseCodePacket(key, pin)
    
    assert packet.opcode == BoksCommandOpcode.CREATE_SINGLE_USE_CODE
    
    full_packet = packet.to_bytes()
    # Structure: [Opcode][Len][Key(8)][PIN(6)][CRC]
    assert full_packet[0] == BoksCommandOpcode.CREATE_SINGLE_USE_CODE
    assert full_packet[1] == 14 # 8+6
    assert full_packet[2:10] == key.encode('ascii')
    assert full_packet[10:16] == pin.encode('ascii')
