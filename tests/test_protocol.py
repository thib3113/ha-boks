"""Tests for Boks protocol."""
from custom_components.boks.ble.protocol import BoksProtocol

def test_calculate_checksum():
    """Test checksum calculation."""
    data = bytearray([0x01, 0x02, 0x03])
    # 1+2+3 = 6
    assert BoksProtocol.calculate_checksum(data) == 6
    
    data = bytearray([0xFF, 0x01])
    # 255 + 1 = 256 -> 0 (8-bit)
    assert BoksProtocol.calculate_checksum(data) == 0

def test_parse_battery_stats_valid_6_bytes():
    """Test parse_battery_stats with 6 bytes format."""
    # [100, 90, 95, 100, 98, Temp]
    # Temp = 45 -> 45 - 25 = 20 C
    payload = bytearray([100, 90, 95, 100, 98, 45])
    stats = BoksProtocol.parse_battery_stats(payload)
    
    assert stats is not None
    assert stats["format"] == "measures-first-min-mean-max-last"
    assert stats["level_first"] == 100
    assert stats["level_min"] == 90
    assert stats["level_mean"] == 95
    assert stats["level_max"] == 100
    assert stats["level_last"] == 98
    assert stats["temperature"] == 20

def test_parse_battery_stats_valid_4_bytes():
    """Test parse_battery_stats with 4 bytes format."""
    # [100, 90, 80, Temp]
    payload = bytearray([100, 90, 80, 50])
    stats = BoksProtocol.parse_battery_stats(payload)
    
    assert stats is not None
    assert stats["format"] == "measures-t1-t5-t10"
    assert stats["level_t1"] == 100
    assert stats["level_t5"] == 90
    assert stats["level_t10"] == 80
    assert stats["temperature"] == 25

def test_parse_battery_stats_invalid():
    """Test parse_battery_stats with invalid payloads."""
    # Empty
    assert BoksProtocol.parse_battery_stats(b"") is None
    
    # All FF
    assert BoksProtocol.parse_battery_stats(b"\xFF\xFF\xFF\xFF\xFF\xFF") is None
    
    # Wrong length
    assert BoksProtocol.parse_battery_stats(b"\x00\x00") is None
