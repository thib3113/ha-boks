"""Test for CodeConversionPacket."""

from custom_components.boks.ble.const import BoksCommandOpcode
from custom_components.boks.packets.tx.code_conversion import CodeConversionPacket


def test_CodeConversionPacket_init():
    """Test initialization of CodeConversionPacket."""
    # Test S->M conversion
    opcode = BoksCommandOpcode.SINGLE_USE_CODE_TO_MULTI
    config_key = "12345678"
    code_value = "87654321"

    packet = CodeConversionPacket(opcode, config_key, code_value)

    assert packet.opcode == opcode
    assert packet.config_key == config_key
    assert packet.code_value == code_value

    full_packet = packet.to_bytes()
    # Structure: [Opcode][Len][ConfigKey(8)][CodeValue(NB)][CRC]
    assert full_packet[0] == opcode
    assert full_packet[1] == len(config_key) + len(code_value)
    assert full_packet[2:10] == config_key.encode("ascii")
    assert full_packet[10 : 10 + len(code_value)] == code_value.encode("ascii")

    # Test M->S conversion
    opcode_ms = BoksCommandOpcode.MULTI_CODE_TO_SINGLE_USE
    packet_ms = CodeConversionPacket(opcode_ms, config_key, code_value)
    assert packet_ms.opcode == opcode_ms
    assert packet_ms.to_bytes()[0] == opcode_ms


def test_CodeConversionPacket_log():
    """Test logging of CodeConversionPacket."""
    opcode = BoksCommandOpcode.SINGLE_USE_CODE_TO_MULTI
    config_key = "12345678"
    code_value = "87654321"
    packet = CodeConversionPacket(opcode, config_key, code_value)

    # Test without anonymization
    log_dict = packet.to_log_dict(anonymize=False)
    assert "Type=S->M" in log_dict["payload"]
    assert f"Key={config_key}" in log_dict["payload"]
    assert f"Code={code_value}" in log_dict["payload"]
    assert log_dict["suffix"] == ""

    # Test with anonymization
    log_dict_anon = packet.to_log_dict(anonymize=True)
    assert "Type=S->M" in log_dict_anon["payload"]
    assert config_key not in log_dict_anon["payload"]
    assert code_value not in log_dict_anon["payload"]
    assert "Key=********" in log_dict_anon["payload"]
    assert "Code=******" in log_dict_anon["payload"]
    assert "(ANONYMIZED)" in log_dict_anon["suffix"]
