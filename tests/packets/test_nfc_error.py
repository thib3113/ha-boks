"""Test for NfcErrorPacket."""
import pytest
from custom_components.boks.packets.rx.nfc_error import NfcErrorPacket
from custom_components.boks.ble.const import BoksHistoryEvent, BoksNotificationOpcode

def test_parse_nfc_error(mock_time, packet_builder):
    """Test parsing NfcErrorPacket."""
    # TODO: Define valid payload
    payload = bytes.fromhex("000000")
    # Use opcode from class if available, or placeholder
    opcode = 0x00

    data = packet_builder(opcode, payload)

    # Check if class allows instantiation with just data or opcode+data
    try:
        packet = NfcErrorPacket(data)
    except TypeError:
        packet = NfcErrorPacket(opcode, data)

    assert packet.opcode == opcode