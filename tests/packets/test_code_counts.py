"""Test for CodeCountsPacket."""
from custom_components.boks.packets.rx.code_counts import CodeCountsPacket
from custom_components.boks.ble.const import BoksNotificationOpcode

def test_parse_code_counts(mock_time, packet_builder):
    """Test parsing CodeCountsPacket."""
    # Define valid payload: 5 master codes, 10 single use codes
    # [MasterCount_MSB][MasterCount_LSB][SingleUseCount_MSB][SingleUseCount_LSB]
    payload = bytes.fromhex("0005000A")
    opcode = BoksNotificationOpcode.NOTIFY_CODES_COUNT
    
    data = packet_builder(opcode, payload)
    packet = CodeCountsPacket(data)
    
    assert packet.opcode == opcode
    assert packet.master_count == 5
    assert packet.single_use_count == 10
    assert packet.extra_data == {"master": 5, "single_use": 10}
