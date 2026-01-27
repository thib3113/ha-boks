"""Test for ErrorLogPacket."""
from custom_components.boks.packets.rx.error_log import ErrorLogPacket
from custom_components.boks.ble.const import BoksHistoryEvent

def test_parse_error_log():
    """Test parsing of ErrorLogPacket."""
    opcode = BoksHistoryEvent.ERROR
    age_bytes = (300).to_bytes(3, 'big')
    error_code = 0x05
    
    raw_data = bytearray()
    raw_data.append(opcode)
    raw_data.append(len(age_bytes) + 1)
    raw_data.extend(age_bytes)
    raw_data.append(error_code)
    checksum = sum(raw_data) & 0xFF
    raw_data.append(checksum)
    
    packet = ErrorLogPacket(raw_data)
    
    assert packet.opcode == opcode
    assert packet.age == 300
    assert packet.error_code == error_code
    assert "error_description" in packet.extra_data
    assert packet.verify_checksum()
