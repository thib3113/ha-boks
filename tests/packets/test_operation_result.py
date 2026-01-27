"""Test for OperationResultPacket."""
import pytest
from custom_components.boks.packets.rx.operation_result import OperationResultPacket
from custom_components.boks.ble.const import BoksHistoryEvent, BoksNotificationOpcode

def test_parse_operation_result(mock_time, packet_builder):
    """Test parsing OperationResultPacket."""
    # TODO: Define valid payload
    payload = bytes.fromhex("000000")
    # Use opcode from class if available, or placeholder
    opcode = 0x00

    data = packet_builder(opcode, payload)

    # Check if class allows instantiation with just data or opcode+data
    try:
        packet = OperationResultPacket(data)
    except TypeError:
        packet = OperationResultPacket(opcode, data)

    assert packet.opcode == opcode