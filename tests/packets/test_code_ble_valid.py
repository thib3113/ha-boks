"""Test for CodeBleValidPacket."""
from custom_components.boks.packets.rx.code_ble_valid import CodeBleValidPacket
from custom_components.boks.ble.const import BoksHistoryEvent

def test_parse_code_ble_valid():
    """Test parsing of CodeBleValidPacket."""
    opcode = BoksHistoryEvent.CODE_BLE_VALID
    age_bytes = (100).to_bytes(3, 'big')
    pin = "123456"
    pin_bytes = pin.encode('ascii')
    
    raw_data = bytearray()
    raw_data.append(opcode)
    raw_data.append(len(age_bytes) + len(pin_bytes))
    raw_data.extend(age_bytes)
    raw_data.extend(pin_bytes)
    checksum = sum(raw_data) & 0xFF
    raw_data.append(checksum)
    
    packet = CodeBleValidPacket(raw_data)
    
    assert packet.opcode == opcode
    assert packet.age == 100
    assert packet.pin == pin
    assert packet.extra_data["code"] == pin
    assert packet.verify_checksum()