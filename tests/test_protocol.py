"""Tests for the Boks Protocol logic."""
import pytest
from custom_components.boks.ble.protocol import BoksProtocol

def test_calculate_checksum():
    """Test checksum calculation."""
    # Simple sum: 1 + 2 + 3 = 6
    data = bytearray([0x01, 0x02, 0x03])
    assert BoksProtocol.calculate_checksum(data) == 0x06
    
    # Overflow: 255 + 1 = 256 -> 0 (modulo 256)
    data = bytearray([0xFF, 0x01])
    assert BoksProtocol.calculate_checksum(data) == 0x00

def test_build_packet():
    """Test packet building."""
    opcode = 0x10
    payload = b"\x01\x02"
    
    # Expected: [Opcode, Len(2), 0x01, 0x02, Checksum]
    # Checksum: 0x10 + 0x02 + 0x01 + 0x02 = 0x15 (21)
    expected = bytearray([0x10, 0x02, 0x01, 0x02, 0x15])
    
    packet = BoksProtocol.build_packet(opcode, payload)
    assert packet == expected

def test_verify_checksum():
    """Test checksum validation."""
    # Valid packet: [0x01, 0x01 (checksum)]
    assert BoksProtocol.verify_checksum(bytearray([0x01, 0x01])) is True
    
    # Invalid packet
    assert BoksProtocol.verify_checksum(bytearray([0x01, 0x02])) is False
    
    # Empty packet
    assert BoksProtocol.verify_checksum(bytearray()) is False

def test_parse_door_status():
    """Test parsing door status."""
    # Open: [Opcode, Len, Inverted(0), Live(1), Checksum]
    data_open = bytearray([0x65, 0x02, 0x00, 0x01, 0xFF])
    assert BoksProtocol.parse_door_status(data_open) is True
    
    # Closed: [Opcode, Len, Inverted(0), Live(0), Checksum]
    data_closed = bytearray([0x65, 0x02, 0x00, 0x00, 0xFF])
    assert BoksProtocol.parse_door_status(data_closed) is False
    
    # Invalid (too short)
    assert BoksProtocol.parse_door_status(bytearray([0x65])) is None

def test_parse_code_counts():
    """Test parsing code counts."""
    # Payload: Master(2) + Single(2)
    # Master = 1 (0x0001), Single = 256 (0x0100)
    payload = b"\x00\x01\x01\x00"
    counts = BoksProtocol.parse_code_counts(payload)
    assert counts == {"master": 1, "single_use": 256}

def test_parse_battery_stats():
    """Test parsing battery stats."""
    # 6-byte format: [First, Min, Mean, Max, Last, Temp(Raw)]
    # Temp Raw 50 (50-25 = 25°C)
    payload_6 = b"\x28\x28\x2A\x2C\x2A\x32" # 4.0, 4.0, 4.2, 4.4, 4.2V, 25°C
    stats = BoksProtocol.parse_battery_stats(payload_6)
    assert stats["format"] == "measures-first-min-mean-max-last"
    assert stats["level_last"] == 42 # 0x2A
    assert stats["temperature"] == 25
    
    # 4-byte format: [T1, T5, T10, Temp]
    payload_4 = b"\x28\x2A\x2C\x32"
    stats = BoksProtocol.parse_battery_stats(payload_4)
    assert stats["format"] == "measures-t1-t5-t10"
    assert stats["level_t5"] == 42 # 0x2A
    
    # Invalid (All FF)
    payload_invalid = b"\xFF\xFF\xFF\xFF\xFF\xFF"
    assert BoksProtocol.parse_battery_stats(payload_invalid) is None
