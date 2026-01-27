"""Test for AskDoorStatusPacket."""
from custom_components.boks.packets.tx.ask_door_status import AskDoorStatusPacket
from custom_components.boks.ble.const import BoksCommandOpcode

def test_AskDoorStatusPacket_init():
    """Test initialization of AskDoorStatusPacket."""
    packet = AskDoorStatusPacket()
    assert packet.opcode == BoksCommandOpcode.ASK_DOOR_STATUS
    assert packet.to_bytes() == bytearray([BoksCommandOpcode.ASK_DOOR_STATUS, 0x00, BoksCommandOpcode.ASK_DOOR_STATUS])