"""Error classes for Boks."""
from .boks_auth_error import BoksAuthError
from .boks_command_error import BoksCommandError
from .boks_error import BoksError

__all__ = [
    "BoksError",
    "BoksAuthError",
    "BoksCommandError",
]
