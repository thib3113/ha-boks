import logging

from homeassistant.components.event import (
    EventEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, EVENT_LOG
from .ble.const import LOG_EVENT_TYPES
from .coordinator import BoksDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Boks event entity."""
    coordinator: BoksDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([BoksLogEvent(coordinator, entry)])

class BoksLogEvent(CoordinatorEntity, EventEntity):
    """Representation of a Boks Log Event."""

    _attr_has_entity_name = True
    _attr_translation_key = "logs"
    _attr_event_types = list(LOG_EVENT_TYPES.values()) + ["unknown"]

    def __init__(self, coordinator: BoksDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the event."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.data[CONF_MAC]}_logs"
        self._last_log_timestamp = None

    @property
    def suggested_object_id(self) -> str | None:
        """Return the suggested object id."""
        return "logs"

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._entry.data[CONF_MAC])},
            "name": self._entry.data.get(CONF_NAME) or f"Boks {self._entry.data[CONF_MAC]}",
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        latest_logs = self.coordinator.data.get("latest_logs")
        last_fetch = self.coordinator.data.get("last_log_fetch_ts")

        if latest_logs and last_fetch != self._last_log_timestamp:
            self._last_log_timestamp = last_fetch
            
            # Process new logs
            for i, log in enumerate(latest_logs):
                # Skip None log entries
                if log is None:
                    _LOGGER.warning("Skipping None log entry at index %d", i)
                    continue
                    
                # Debug logging to verify data flow
                _LOGGER.debug("Processing log entry at index %d: %s (type: %s)", i, log, type(log))
                
                # Create a clean dictionary for the event data
                event_type = log.get("event_type", "unknown") if isinstance(log, dict) else getattr(log, "event_type", "unknown")
                
                # Get device_id for logbook integration
                device_registry = dr.async_get(self.hass)
                device_entry = device_registry.async_get_device(identifiers={(DOMAIN, self._entry.data[CONF_MAC])})
                device_id = device_entry.id if device_entry else None
                
                # Safely access log attributes with fallbacks
                opcode = log.get("opcode", "unknown") if isinstance(log, dict) else getattr(log, "opcode", "unknown")
                payload = log.get("payload", "") if isinstance(log, dict) else getattr(log, "payload", "")
                timestamp = log.get("timestamp", None) if isinstance(log, dict) else getattr(log, "timestamp", None)
                description = log.get("description", "Unknown Event") if isinstance(log, dict) else getattr(log, "description", "Unknown Event")
                
                # Additional safety check for None values
                if opcode is None:
                    opcode = "unknown"
                if payload is None:
                    payload = ""
                if description is None:
                    description = "Unknown Event"
                if event_type is None:
                    event_type = "unknown"
                
                data = {
                    "opcode": opcode,
                    "payload": payload,
                    "timestamp": timestamp,
                    "description": description,
                    "type": event_type,
                    "device_id": device_id,
                }
                
                # Add extra_data if present
                if isinstance(log, dict):
                    known_fields = {"opcode", "payload", "timestamp", "event_type", "description", "type"}
                    extra_data = {k: v for k, v in log.items() if k not in known_fields}
                else:
                    # For object-based logs, we can't easily extract extra data
                    # Let's try to access a 'details' attribute if it exists
                    extra_data = {}
                    # Safety check for None log object
                    if log is not None and hasattr(log, 'details') and log.details is not None:
                        # If details is a dict, merge it into extra_data
                        if isinstance(log.details, dict):
                            extra_data.update(log.details)
                        else:
                            # Otherwise, add it as a 'details' field
                            extra_data['details'] = log.details
                    
                # Additional safety check for extra_data
                if extra_data is None:
                    extra_data = {}
                    
                if extra_data:
                    # Ensure all values in extra_data are serializable
                    safe_extra_data = {}
                    for k, v in extra_data.items():
                        if v is not None:
                            safe_extra_data[k] = v
                        else:
                            safe_extra_data[k] = "None"
                    data["extra_data"] = safe_extra_data

                # Convert bytes to hex if needed
                if isinstance(data["payload"], bytes):
                    data["payload"] = data["payload"].hex()
                elif data["payload"] is None:
                    data["payload"] = ""

                # Trigger the event with the specific event type as the state
                _LOGGER.debug("Triggering event: %s with data: %s", event_type, data)
                self._trigger_event(event_type, data)
                self.hass.bus.async_fire(EVENT_LOG, data)
            
        super()._handle_coordinator_update()
