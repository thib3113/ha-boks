"""Test for BleRebootPacket."""
from custom_components.boks.packets.rx.ble_reboot import BleRebootPacket
from custom_components.boks.ble.const import BoksHistoryEvent

def test_parse_ble_reboot():
    """Test parsing of BleRebootPacket."""
    # Opcode(1) + Len(1) + Age(3) + Checksum(1)
    # Len = 3
    opcode = BoksHistoryEvent.BLE_REBOOT
    age_bytes = (10).to_bytes(3, 'big')
    
    # Build raw data manually
    raw_data = bytearray()
    raw_data.append(opcode)
    raw_data.append(len(age_bytes))
    raw_data.extend(age_bytes)
    checksum = sum(raw_data) & 0xFF
    raw_data.append(checksum)
    
    packet = BleRebootPacket(raw_data)
    
    assert packet.opcode == opcode
    assert packet.age == 10
    assert packet.to_bytes() == raw_data
    assert packet.verify_checksum()
