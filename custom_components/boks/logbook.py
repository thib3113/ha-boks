"""Describe logbook events for Boks integration."""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from homeassistant.components.logbook import LOGBOOK_ENTRY_MESSAGE, LOGBOOK_ENTRY_NAME
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, callback

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
        device_id = data.get("device_id")

        # The message is now pre-translated and formatted by the coordinator in the 'description' field
        message = data.get("description", "Unknown Event")

        return {
            LOGBOOK_ENTRY_NAME: "",
            LOGBOOK_ENTRY_MESSAGE: message,
            ATTR_DEVICE_ID: device_id,
        }

    async_describe_event(DOMAIN, EVENT_LOG, async_describe_log_event)
