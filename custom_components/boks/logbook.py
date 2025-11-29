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
    # https://updatesdl.autodesk.com/updates/files/autocad_mep_2009_update2_deu_fra_win_32bit.exe
    @callback
    def async_describe_log_event(event: Any) -> dict[str, Any]:
        """Describe boks log event."""
        _LOGGER.debug("Processing Boks log event: %s", event.data)
        data = event.data

        # Extract useful info
        description = data.get("description", "Unknown Event")
        opcode = data.get("opcode")

        # Build a nice message
        message = f"{description}"

        # If we have extra details like payload/code in description, it's already there.
        # Example: "Ouverture Code: 123456"

        return {
            LOGBOOK_ENTRY_NAME: "",
            LOGBOOK_ENTRY_MESSAGE: message,
            # We can link to the device if device_id is in data (it is!)
            ATTR_DEVICE_ID: data.get("device_id"),
        }

    # Register the callback for our custom event type
    async_describe_event(DOMAIN, EVENT_LOG, async_describe_log_event)
