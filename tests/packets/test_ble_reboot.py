"""Test for BleRebootPacket."""
import pytest
from custom_components.boks.packets.rx.ble_reboot import BleRebootPacket
from custom_components.boks.ble.const import BoksHistoryEvent, BoksNotificationOpcode

def test_parse_ble_reboot(mock_time, packet_builder):
    """Test parsing BleRebootPacket."""
    # TODO: Define valid payload
    payload = bytes.fromhex("000000")
    # Use opcode from class if available, or placeholder
    opcode = BoksHistoryEvent.BLE_REBOOT

    data = packet_builder(opcode, payload)

    # Check if class allows instantiation with just data or opcode+data
    try:
        packet = BleRebootPacket(data)
    except TypeError:
        packet = BleRebootPacket(opcode, data)

    assert packet.opcode == opcode