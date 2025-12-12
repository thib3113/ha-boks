"""Tests for the Boks parcels utils."""
import pytest
import re
from custom_components.boks.parcels.utils import (
    parse_parcel_string,
    generate_random_code,
    format_parcel_item,
    BOKS_CHAR_MAP,
    PARCEL_REGEX
)

def test_parse_parcel_string_with_valid_code():
    """Test parsing a string with a valid code and description."""
    # Test with space separator
    code, description = parse_parcel_string("123456 Test parcel")
    assert code == "123456"
    assert description == "Test parcel"
    
    # Test with dash separator
    code, description = parse_parcel_string("123456 - Test parcel")
    assert code == "123456"
    assert description == "Test parcel"
    
    # Test with colon separator
    code, description = parse_parcel_string("123456: Test parcel")
    assert code == "123456"
    assert description == "Test parcel"
    
    # Test with mixed case code
    code, description = parse_parcel_string("aB1234 - Test parcel")
    assert code == "AB1234"
    assert description == "Test parcel"

def test_parse_parcel_string_without_code():
    """Test parsing a string without a valid code."""
    # Test with just description
    code, description = parse_parcel_string("Just a description")
    assert code is None
    assert description == "Just a description"
    
    # Test with invalid code length
    code, description = parse_parcel_string("12345 Test parcel")
    assert code is None
    assert description == "12345 Test parcel"
    
    # Test with invalid characters in code
    code, description = parse_parcel_string("12345G Test parcel")
    assert code is None
    assert description == "12345G Test parcel"
    
    # Test with code only (no separator)
    code, description = parse_parcel_string("123456")
    assert code == "123456"
    assert description == ""

def test_parse_parcel_string_edge_cases():
    """Test edge cases for parsing."""
    # Test with empty string
    code, description = parse_parcel_string("")
    assert code is None
    assert description == ""
    
    # Test with only spaces
    code, description = parse_parcel_string("   ")
    assert code is None
    assert description == ""
    
    # Test with code only
    code, description = parse_parcel_string("123456")
    assert code == "123456"
    assert description == ""
    
    # Test with leading/trailing spaces
    code, description = parse_parcel_string("  123456 - Test parcel  ")
    assert code == "123456"
    assert description == "Test parcel"

def test_generate_random_code():
    """Test generating random codes."""
    # Generate multiple codes to check they're valid
    for _ in range(10):
        code = generate_random_code()
        assert len(code) == 6
        assert all(c in BOKS_CHAR_MAP for c in code)
        # Check that it matches our regex pattern
        match = PARCEL_REGEX.match(code)
        assert match is not None
        assert match.group(1) == code

def test_format_parcel_item_with_code():
    """Test formatting items with a code."""
    # Test with code and description
    result = format_parcel_item("123456", "Test parcel")
    assert result == "123456 - Test parcel"
    
    # Test with code only
    result = format_parcel_item("123456", "")
    assert result == "123456"
    
    # Test with code that's already in description
    result = format_parcel_item("123456", "123456 Test parcel")
    assert result == "123456 Test parcel"

def test_format_parcel_item_without_code():
    """Test formatting items without a code."""
    # Test with description only
    result = format_parcel_item(None, "Test parcel")
    assert result == "Test parcel"
    
    # Test with empty description
    result = format_parcel_item(None, "")
    assert result == ""

def test_boks_char_map():
    """Test that BOKS_CHAR_MAP contains expected characters."""
    expected_chars = "0123456789AB"
    assert BOKS_CHAR_MAP == expected_chars
    # Ensure all characters are valid hex characters
    for char in BOKS_CHAR_MAP:
        assert char in "0123456789ABCDEF"

def test_parcel_regex():
    """Test that PARCEL_REGEX works as expected."""
    # Test valid matches
    match = PARCEL_REGEX.match("123456 Test parcel")
    assert match is not None
    assert match.group(1) == "123456"
    assert match.group(2) == "Test parcel"
    
    # Test case insensitive
    match = PARCEL_REGEX.match("ab1234 Test parcel")
    assert match is not None
    assert match.group(1) == "ab1234"
    
    # Test with special characters in separator
    match = PARCEL_REGEX.match("123456...Test parcel")
    assert match is not None
    assert match.group(1) == "123456"
    assert match.group(2) == "Test parcel"
    
    # Test with dash separator
    match = PARCEL_REGEX.match("123456-Test parcel")
    assert match is not None
    assert match.group(1) == "123456"
    assert match.group(2) == "Test parcel"
    
    # Test with colon separator
    match = PARCEL_REGEX.match("123456:Test parcel")
    assert match is not None
    assert match.group(1) == "123456"
    assert match.group(2) == "Test parcel"