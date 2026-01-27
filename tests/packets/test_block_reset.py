"""Test for BlockResetPacket."""
from custom_components.boks.packets.rx.block_reset import BlockResetPacket
from custom_components.boks.ble.const import BoksHistoryEvent

def test_parse_block_reset():
    """Test parsing of BlockResetPacket."""
    # Opcode(1) + Len(1) + Age(3) + Info(2) + Checksum(1)
    opcode = BoksHistoryEvent.BLOCK_RESET
    age_bytes = (123).to_bytes(3, 'big')
    info_bytes = bytes([0xAA, 0xBB])
    
    raw_data = bytearray()
    raw_data.append(opcode)
    raw_data.append(len(age_bytes) + len(info_bytes))
    raw_data.extend(age_bytes)
    raw_data.extend(info_bytes)
    checksum = sum(raw_data) & 0xFF
    raw_data.append(checksum)
    
    packet = BlockResetPacket(raw_data)
    
    assert packet.opcode == opcode
    assert packet.age == 123
    assert packet.reset_info == "aabb"
    assert packet.extra_data["reset_info"] == "aabb"
    assert packet.verify_checksum()
