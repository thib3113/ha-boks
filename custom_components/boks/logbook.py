"""Describe logbook events for Boks integration."""
from __future__ import annotations

import logging
from typing import Any
from collections.abc import Callable

from homeassistant.components.logbook import LOGBOOK_ENTRY_MESSAGE, LOGBOOK_ENTRY_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import ATTR_DEVICE_ID

from .const import DOMAIN, EVENT_LOG

_LOGGER = logging.getLogger(__name__)

@callback
def async_describe_events(
    hass: HomeAssistant,
    async_describe_event: Callable[[str, str, Callable[[Any], dict[str, Any]]], None],
) -> None:
    """Describe logbook events."""
    _LOGGER.debug("Registering logbook events for Boks")

    @callback
    def async_describe_log_event(event: Any) -> dict[str, Any]:
        """Describe boks log event."""
        _LOGGER.debug("Processing Boks log event: %s", event.data)
        data = event.data

        # Extract useful info
        description_key = data.get("description", "unknown")

        # Try to find the translation in our cache
        # The cache contains the 'state' dict from entity.event.logs, so keys are 'door_closed', 'door_opened', etc.
        translations = hass.data.get(DOMAIN, {}).get("translations", {})

        message = translations.get(description_key, description_key)

        return {
            LOGBOOK_ENTRY_NAME: "",
            LOGBOOK_ENTRY_MESSAGE: message,
            ATTR_DEVICE_ID: data.get("device_id"),
        }

    async_describe_event(DOMAIN, EVENT_LOG, async_describe_log_event)
