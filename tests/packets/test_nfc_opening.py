"""Test for NfcOpeningPacket."""
import pytest
from custom_components.boks.packets.rx.nfc_opening import NfcOpeningPacket
from custom_components.boks.ble.const import BoksHistoryEvent

def test_parse_nfc_opening(mock_time, packet_builder):
    """Test parsing NfcOpeningPacket."""
    # Payload: Age(3) + TagType(1) + Len(1) + UID(...)
    # Type 1 (La Poste), Len 4, UID A1B2C3D4
    payload = bytes.fromhex("00000A0104A1B2C3D4")
    data = packet_builder(BoksHistoryEvent.NFC_OPENING, payload)

    packet = NfcOpeningPacket(data)

    assert packet.opcode == BoksHistoryEvent.NFC_OPENING
    assert packet.extra_data["tag_uid"] == "A1B2C3D4"
    assert packet.extra_data["tag_type"] == 1