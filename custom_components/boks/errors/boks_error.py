"""Base exception class for Boks errors."""
from typing import Dict


class BoksError(Exception):
    """Base class for Boks errors."""
    def __init__(self, translation_key: str, translation_placeholders: Dict[str, str] | None = None):
        super().__init__(translation_key) # For generic Exception message if not translated by HA
        self.translation_key = translation_key
        self.translation_placeholders = translation_placeholders or {}