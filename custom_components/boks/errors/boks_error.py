"""Base exception class for Boks errors."""
from homeassistant.exceptions import HomeAssistantError
from ..const import DOMAIN

class BoksError(HomeAssistantError):
    """Base class for Boks errors."""
    def __init__(self, translation_key: str, translation_placeholders: dict[str, str] | None = None):
        super().__init__(
            translation_domain=DOMAIN,
            translation_key=translation_key,
            translation_placeholders=translation_placeholders
        )
