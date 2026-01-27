"""Test for CodeKeyValidPacket."""
from custom_components.boks.packets.rx.code_key_valid import CodeKeyValidPacket
from custom_components.boks.ble.const import BoksHistoryEvent

def test_parse_code_key_valid():
    """Test parsing of CodeKeyValidPacket."""
    opcode = BoksHistoryEvent.CODE_KEY_VALID
    age_bytes = (200).to_bytes(3, 'big')
    pin = "654321"
    pin_bytes = pin.encode('ascii')
    
    raw_data = bytearray()
    raw_data.append(opcode)
    raw_data.append(len(age_bytes) + len(pin_bytes))
    raw_data.extend(age_bytes)
    raw_data.extend(pin_bytes)
    checksum = sum(raw_data) & 0xFF
    raw_data.append(checksum)
    
    packet = CodeKeyValidPacket(raw_data)
    
    assert packet.opcode == opcode
    assert packet.age == 200
    assert packet.pin == pin
    assert packet.extra_data["code"] == pin
    assert packet.verify_checksum()
