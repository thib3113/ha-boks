"""Test for SetConfigurationPacket."""
from custom_components.boks.packets.tx.set_configuration import SetConfigurationPacket
from custom_components.boks.ble.const import BoksCommandOpcode, BoksConfigType

def test_SetConfigurationPacket_init():
    """Test initialization of SetConfigurationPacket."""
    key = "CONFKEY1"
    config_type = BoksConfigType.SCAN_LAPOSTE_NFC_TAGS
    value = True
    packet = SetConfigurationPacket(key, config_type, value)
    
    assert packet.opcode == BoksCommandOpcode.SET_CONFIGURATION
    
    full_packet = packet.to_bytes()
    # Structure: [Opcode][Len][Key(8)][Type(1)][Value(1)][CRC]
    assert full_packet[0] == BoksCommandOpcode.SET_CONFIGURATION
    assert full_packet[1] == 10 # 8+1+1
    assert full_packet[2:10] == key.encode('ascii')
    assert full_packet[10] == config_type
    assert full_packet[11] == 1  # True
