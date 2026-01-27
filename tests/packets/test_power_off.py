"""Test for PowerOffPacket."""
import pytest
from custom_components.boks.packets.rx.power_off import PowerOffPacket
from custom_components.boks.ble.const import BoksHistoryEvent

def test_parse_power_off(mock_time, packet_builder):
    """Test parsing PowerOffPacket."""
    # Payload: Age(3) + Reason(1)
    # Reason 2 = Watchdog
    payload = bytes.fromhex("00000A02")
    data = packet_builder(BoksHistoryEvent.POWER_OFF, payload)

    packet = PowerOffPacket(data)

    assert packet.opcode == BoksHistoryEvent.POWER_OFF
    assert packet.reason_code == 2
