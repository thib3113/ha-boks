"""Test for NfcScanResultPacket."""
import pytest
from custom_components.boks.packets.rx.nfc_scan_result import NfcScanResultPacket
from custom_components.boks.ble.const import BoksHistoryEvent, BoksNotificationOpcode

def test_parse_nfc_scan_result(mock_time, packet_builder):
    """Test parsing NfcScanResultPacket."""
    # TODO: Define valid payload
    payload = bytes.fromhex("000000")
    # Use opcode from class if available, or placeholder
    opcode = 0x00

    data = packet_builder(opcode, payload)

    # Check if class allows instantiation with just data or opcode+data
    try:
        packet = NfcScanResultPacket(data)
    except TypeError:
        packet = NfcScanResultPacket(opcode, data)

    assert packet.opcode == opcode