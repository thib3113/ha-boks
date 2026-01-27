"""Tests for Boks exceptions."""
from custom_components.boks.errors import BoksError, BoksAuthError, BoksCommandError

def test_boks_error():
    """Test BoksError."""
    err = BoksError("error_code", {"key": "value"})
    assert str(err) == "error_code"
    assert err.translation_key == "error_code"
    assert err.translation_placeholders == {"key": "value"}

def test_boks_auth_error():
    """Test BoksAuthError."""
    err = BoksAuthError("auth_failed")
    assert isinstance(err, BoksError)

def test_boks_command_error():
    """Test BoksCommandError."""
    err = BoksCommandError("cmd_failed")
    assert isinstance(err, BoksError)
