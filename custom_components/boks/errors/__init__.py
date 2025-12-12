"""Error classes for Boks."""
from .boks_error import BoksError
from .boks_auth_error import BoksAuthError
from .boks_command_error import BoksCommandError

__all__ = [
    "BoksError",
    "BoksAuthError",
    "BoksCommandError",
]