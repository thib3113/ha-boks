"""Test for NfcTagRegisteringScanPacket."""
import pytest
from custom_components.boks.packets.rx.nfc_tag_registering_scan import NfcTagRegisteringScanPacket
from custom_components.boks.ble.const import BoksHistoryEvent

def test_parse_nfc_tag_registering_scan(mock_time, packet_builder):
    """Test parsing NfcTagRegisteringScanPacket."""
    # Payload: Age(3) + Type(1) + Len(1) + UID(...)
    # Type 1, Len 4, UID AABBCCDD
    payload = bytes.fromhex("00000A0104AABBCCDD")
    data = packet_builder(BoksHistoryEvent.NFC_TAG_REGISTERING_SCAN, payload)

    packet = NfcTagRegisteringScanPacket(data)

    assert packet.opcode == BoksHistoryEvent.NFC_TAG_REGISTERING_SCAN
    assert packet.extra_data["scan_uid"] == "AABBCCDD"
