"""Test for CodeBleValidPacket."""
import pytest
from custom_components.boks.packets.rx.code_ble_valid import CodeBleValidPacket
from custom_components.boks.ble.const import BoksHistoryEvent

def test_parse_code_ble_valid(mock_time, packet_builder):
    """Test parsing CodeBleValidPacket."""
    payload = bytes.fromhex("000064313233343536")
    data = packet_builder(BoksHistoryEvent.CODE_BLE_VALID, payload)

    packet = CodeBleValidPacket(data)

    assert packet.opcode == BoksHistoryEvent.CODE_BLE_VALID
    assert packet.extra_data["code"] == "123456"
