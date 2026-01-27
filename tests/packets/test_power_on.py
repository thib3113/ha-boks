"""Test for PowerOnPacket."""
from custom_components.boks.packets.rx.power_on import PowerOnPacket
from custom_components.boks.ble.const import BoksHistoryEvent

def test_parse_power_on():
    """Test parsing of PowerOnPacket."""
    opcode = BoksHistoryEvent.POWER_ON
    age_bytes = (0).to_bytes(3, 'big')
    
    raw_data = bytearray()
    raw_data.append(opcode)
    raw_data.append(len(age_bytes))
    raw_data.extend(age_bytes)
    checksum = sum(raw_data) & 0xFF
    raw_data.append(checksum)
    
    packet = PowerOnPacket(raw_data)
    
    assert packet.opcode == opcode
    assert packet.verify_checksum()
