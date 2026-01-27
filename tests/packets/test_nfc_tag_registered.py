"""Test for NfcTagRegisteredPacket."""
import pytest
from custom_components.boks.packets.rx.nfc_tag_registered import NfcTagRegisteredPacket
from custom_components.boks.ble.const import BoksHistoryEvent, BoksNotificationOpcode

def test_parse_nfc_tag_registered(mock_time, packet_builder):
    """Test parsing NfcTagRegisteredPacket."""
    # TODO: Define valid payload
    payload = bytes.fromhex("000000")
    # Use opcode from class if available, or placeholder
    opcode = BoksNotificationOpcode.NOTIFY_NFC_TAG_REGISTERED

    data = packet_builder(opcode, payload)

    # Check if class allows instantiation with just data or opcode+data
    try:
        packet = NfcTagRegisteredPacket(data)
    except TypeError:
        packet = NfcTagRegisteredPacket(opcode, data)

    assert packet.opcode == opcode