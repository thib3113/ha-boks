"""Test for GetLogsCountPacket."""
from custom_components.boks.packets.tx.get_logs_count import GetLogsCountPacket
from custom_components.boks.ble.const import BoksCommandOpcode

def test_GetLogsCountPacket_init():
    """Test initialization of GetLogsCountPacket."""
    packet = GetLogsCountPacket()
    assert packet.opcode == BoksCommandOpcode.GET_LOGS_COUNT
    assert packet.to_bytes() == bytearray([BoksCommandOpcode.GET_LOGS_COUNT, 0x00, BoksCommandOpcode.GET_LOGS_COUNT])