"""Tests for the Boks PIN Generator."""
import pytest
from custom_components.boks.logic.pin_generator import BoksPinGenerator
from custom_components.boks.errors import BoksError

# 32 bytes master key (64 hex chars)
VALID_MASTER_KEY = "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"

def test_init_valid_key():
    """Test initialization with a valid key."""
    generator = BoksPinGenerator(VALID_MASTER_KEY)
    assert generator.master_key == VALID_MASTER_KEY

def test_init_none_key():
    """Test initialization with None key."""
    generator = BoksPinGenerator(None)
    assert generator.master_key is None

def test_generate_pin_master_valid():
    """Test generating a master PIN."""
    generator = BoksPinGenerator(VALID_MASTER_KEY)
    pin = generator.generate_pin("master", 0)
    assert len(pin) == 6
    assert all(c in "0123456789AB" for c in pin)
    
    # Check determinism
    pin2 = generator.generate_pin("master", 0)
    assert pin == pin2

def test_generate_pin_single_valid():
    """Test generating a single-use PIN."""
    generator = BoksPinGenerator(VALID_MASTER_KEY)
    pin = generator.generate_pin("single", 1)
    assert len(pin) == 6
    assert all(c in "0123456789AB" for c in pin)

def test_generate_pin_multi_valid():
    """Test generating a multi-use PIN."""
    generator = BoksPinGenerator(VALID_MASTER_KEY)
    pin = generator.generate_pin("multi", 2)
    assert len(pin) == 6
    assert all(c in "0123456789AB" for c in pin)

def test_generate_pin_different_indices():
    """Test that different indices produce different PINs."""
    generator = BoksPinGenerator(VALID_MASTER_KEY)
    pin1 = generator.generate_pin("single", 1)
    pin2 = generator.generate_pin("single", 2)
    assert pin1 != pin2

def test_generate_pin_different_types():
    """Test that different types produce different PINs."""
    generator = BoksPinGenerator(VALID_MASTER_KEY)
    pin1 = generator.generate_pin("single", 1)
    pin2 = generator.generate_pin("multi", 1)
    assert pin1 != pin2

def test_generate_pin_missing_key():
    """Test generating PIN without a key raises BoksError."""
    generator = BoksPinGenerator(None)
    with pytest.raises(BoksError) as excinfo:
        generator.generate_pin("master", 0)
    assert excinfo.value.translation_key == "master_key_required"

def test_generate_pin_invalid_key_length():
    """Test generating PIN with invalid key length raises BoksError."""
    # 31 bytes (62 hex chars)
    invalid_key = "00" * 31
    generator = BoksPinGenerator(invalid_key)
    with pytest.raises(BoksError) as excinfo:
        generator.generate_pin("master", 0)
    assert excinfo.value.translation_key == "master_key_invalid"

def test_generate_pin_invalid_key_content():
    """Test generating PIN with non-hex key raises BoksError."""
    invalid_key = "ZZ" * 32
    generator = BoksPinGenerator(invalid_key)
    with pytest.raises(BoksError) as excinfo:
        generator.generate_pin("master", 0)
    assert excinfo.value.translation_key == "master_key_invalid"
