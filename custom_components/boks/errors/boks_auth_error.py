"""Exception class for Boks authentication errors."""
from .boks_error import BoksError


class BoksAuthError(BoksError):
    """Exception raised for authentication errors."""
