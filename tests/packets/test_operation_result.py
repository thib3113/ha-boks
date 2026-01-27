"""Test for OperationResultPacket."""
from custom_components.boks.packets.rx.operation_result import OperationResultPacket
from custom_components.boks.ble.const import BoksNotificationOpcode

def test_parse_operation_result():
    # Success
    opcode = BoksNotificationOpcode.CODE_OPERATION_SUCCESS
    raw_data = bytearray([opcode, 0x00, opcode])
    packet = OperationResultPacket(opcode, raw_data)
    assert packet.success is True
    assert packet.verify_checksum()
    
    # Error
    opcode = BoksNotificationOpcode.CODE_OPERATION_ERROR
    raw_data = bytearray([opcode, 0x00, opcode])
    packet = OperationResultPacket(opcode, raw_data)
    assert packet.success is False
    assert packet.verify_checksum()
