"""Test for PowerOffPacket."""
from custom_components.boks.packets.rx.power_off import PowerOffPacket
from custom_components.boks.ble.const import BoksHistoryEvent

def test_parse_power_off():
    """Test parsing of PowerOffPacket."""
    opcode = BoksHistoryEvent.POWER_OFF
    age_bytes = (60).to_bytes(3, 'big')
    reason = 1
    
    raw_data = bytearray()
    raw_data.append(opcode)
    raw_data.append(len(age_bytes) + 1)
    raw_data.extend(age_bytes)
    raw_data.append(reason)
    checksum = sum(raw_data) & 0xFF
    raw_data.append(checksum)
    
    packet = PowerOffPacket(raw_data)
    
    assert packet.opcode == opcode
    assert packet.age == 60
    assert packet.reason_code == reason
    assert packet.verify_checksum()