"""Test for RequestLogsPacket."""
from custom_components.boks.packets.tx.request_logs import RequestLogsPacket
from custom_components.boks.ble.const import BoksCommandOpcode

def test_RequestLogsPacket_init():
    """Test initialization of RequestLogsPacket."""
    packet = RequestLogsPacket()
    assert packet.opcode == BoksCommandOpcode.REQUEST_LOGS
    assert packet.to_bytes() == bytearray([BoksCommandOpcode.REQUEST_LOGS, 0x00, BoksCommandOpcode.REQUEST_LOGS])