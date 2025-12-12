"""Exception class for Boks command errors."""
from .boks_error import BoksError


class BoksCommandError(BoksError):
    """Exception raised for command errors."""