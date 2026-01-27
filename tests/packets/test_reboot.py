"""Test for RebootPacket."""
from custom_components.boks.packets.tx.reboot import RebootPacket
from custom_components.boks.ble.const import BoksCommandOpcode

def test_RebootPacket_init():
    """Test initialization of RebootPacket."""
    packet = RebootPacket()
    assert packet.opcode == BoksCommandOpcode.REBOOT
    assert packet.to_bytes() == bytearray([BoksCommandOpcode.REBOOT, 0x00, BoksCommandOpcode.REBOOT])