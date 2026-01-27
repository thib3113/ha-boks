"""Test for LogCountPacket."""
from custom_components.boks.packets.rx.log_count import LogCountPacket
from custom_components.boks.ble.const import BoksNotificationOpcode

def test_parse_log_count():
    """Test parsing of LogCountPacket."""
    opcode = BoksNotificationOpcode.NOTIFY_LOGS_COUNT
    count_val = 1234 # 0x04D2
    payload = bytes([0x04, 0xD2])
    
    raw_data = bytearray()
    raw_data.append(opcode)
    raw_data.append(len(payload))
    raw_data.extend(payload)
    checksum = sum(raw_data) & 0xFF
    raw_data.append(checksum)
    
    packet = LogCountPacket(raw_data)
    
    assert packet.opcode == opcode
    assert packet.count == 1234
    assert packet.verify_checksum()
