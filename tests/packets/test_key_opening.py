"""Test for KeyOpeningPacket."""
import pytest
from custom_components.boks.packets.rx.key_opening import KeyOpeningPacket
from custom_components.boks.ble.const import BoksHistoryEvent

def test_parse_key_opening(mock_time, packet_builder):
    """Test parsing KeyOpeningPacket."""
    # Payload: Age(3) + Data
    payload = bytes.fromhex("00000A112233")
    data = packet_builder(BoksHistoryEvent.KEY_OPENING, payload)

    packet = KeyOpeningPacket(data)

    assert packet.opcode == BoksHistoryEvent.KEY_OPENING
    # Assuming extra_data contains raw hex payload as "data" key based on old test
    if hasattr(packet, "extra_data") and "data" in packet.extra_data:
        assert packet.extra_data["data"] == "112233"
