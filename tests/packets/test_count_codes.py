from custom_components.boks.packets.tx.count_codes import CountCodesPacket
from custom_components.boks.ble.const import BoksCommandOpcode

def test_count_codes_packet_init():
    """Test initialization of CountCodesPacket."""
    packet = CountCodesPacket()
    assert packet.opcode == BoksCommandOpcode.COUNT_CODES
    assert packet.to_bytes().hex() == "140014"
