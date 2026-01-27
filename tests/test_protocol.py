"""Tests for the Boks Protocol."""
from custom_components.boks.ble.protocol import BoksProtocol

def test_calculate_checksum():
    """Test checksum calculation."""
    # Sum of bytes & 0xFF
    data = bytearray([0x01, 0x02, 0x03])
    # 1+2+3 = 6
    assert BoksProtocol.calculate_checksum(data) == 6

    # Overflow
    data = bytearray([0xFF, 0x02])
    # 255 + 2 = 257 -> 1
    assert BoksProtocol.calculate_checksum(data) == 1

def test_parse_battery_stats_measures_first_min_mean_max_last():
    """Test parsing battery stats (6 bytes)."""
    # [First, Min, Mean, Max, Last, Temp]
    # Temp is raw - 25. If raw=255, None.
    # 0x64 = 100, 0x32 = 50.
    payload = bytes([100, 90, 95, 100, 98, 50]) # Temp 50-25=25
    stats = BoksProtocol.parse_battery_stats(payload)
    
    assert stats is not None
    assert stats["format"] == "measures-first-min-mean-max-last"
    assert stats["level_first"] == 100
    assert stats["level_min"] == 90
    assert stats["level_mean"] == 95
    assert stats["level_max"] == 100
    assert stats["level_last"] == 98
    assert stats["temperature"] == 25

def test_parse_battery_stats_measures_t1_t5_t10():
    """Test parsing battery stats (4 bytes)."""
    # [T1, T5, T10, Temp]
    payload = bytes([100, 255, 255, 45]) # Temp 45-25=20. T5/T10 unavailable (255)
    stats = BoksProtocol.parse_battery_stats(payload)

    assert stats is not None
    assert stats["format"] == "measures-t1-t5-t10"
    assert stats["level_t1"] == 100
    assert stats["level_t5"] is None
    assert stats["level_t10"] is None
    assert stats["temperature"] == 20

def test_parse_battery_stats_invalid():
    """Test parsing invalid battery stats."""
    assert BoksProtocol.parse_battery_stats(b"") is None
    assert BoksProtocol.parse_battery_stats(b"\xFF\xFF\xFF\xFF") is None
    assert BoksProtocol.parse_battery_stats(b"\x00") is None # Wrong length
