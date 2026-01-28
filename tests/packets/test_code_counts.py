"""Test for CodeCountsPacket."""
from custom_components.boks.packets.rx.code_counts import CodeCountsPacket
from custom_components.boks.ble.const import BoksNotificationOpcode

def test_parse_code_counts(mock_time, packet_builder):
    """Test parsing CodeCountsPacket."""
    # TODO: Define valid payload
    payload = bytes.fromhex("000000") 
    # Use opcode from class if available, or placeholder
    opcode = BoksNotificationOpcode.NOTIFY_CODES_COUNT
    
    data = packet_builder(opcode, payload)
    
    # Check if class allows instantiation with just data or opcode+data
    try:
        packet = CodeCountsPacket(data)
    except TypeError:
        packet = CodeCountsPacket(opcode, data)
    
    assert packet.opcode == opcode