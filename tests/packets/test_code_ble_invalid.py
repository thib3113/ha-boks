"""Test for CodeBleInvalidPacket."""
import pytest
from custom_components.boks.packets.rx.code_ble_invalid import CodeBleInvalidPacket
from custom_components.boks.ble.const import BoksHistoryEvent

def test_parse_code_ble_invalid(mock_time, packet_builder):
    """Test parsing CodeBleInvalidPacket."""
    # Payload: Age(3) + Code(6). Code has unprintable.
    # "12" + FF + 00 + "56"
    payload = bytes.fromhex("0000643132FF003536")
    data = packet_builder(BoksHistoryEvent.CODE_BLE_INVALID, payload)
    
    # __init__ takes only raw_data
    packet = CodeBleInvalidPacket(data)
    
    assert packet.opcode == BoksHistoryEvent.CODE_BLE_INVALID
    # "12" + FF(ignored) + 00(kept as NULL) + "56" => "12\x0056"
    assert packet.extra_data["code"] == "12\x0056"
