import logging

from homeassistant.components.event import (
    EventEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .ble.const import LOG_EVENT_TYPES
from .const import DOMAIN, EVENT_LOG
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
        self._attr_unique_id = f"{entry.data[CONF_ADDRESS]}_logs"
        self._last_log_timestamp = None

    @property
    def suggested_object_id(self) -> str | None:
        """Return the suggested object id."""
        return "logs"

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._entry.data[CONF_ADDRESS])},
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        latest_logs = self.coordinator.data.get("latest_logs")
        last_fetch = self.coordinator.data.get("last_log_fetch_ts")

        if latest_logs and last_fetch != self._last_log_timestamp:
            self._last_log_timestamp = last_fetch

            # Get device_id for logbook integration
            device_registry = dr.async_get(self.hass)
            device_entry = device_registry.async_get_device(identifiers={(DOMAIN, self._entry.data[CONF_ADDRESS])})
            device_id = device_entry.id if device_entry else None

            # Process new logs (already enriched by coordinator)
            for log_entry in latest_logs:
                if not log_entry:
                    continue

                event_type = log_entry.get("event_type", "unknown")

                # Prepare final data for bus event
                data = log_entry.copy()
                data["type"] = event_type  # Ensure 'type' field is present for consistency
                data["device_id"] = device_id

                # Flatten extra_data into top level and remove the key
                if "extra_data" in data and isinstance(data["extra_data"], dict):
                    extra = data.pop("extra_data")
                    for key, value in extra.items():
                        if value is not None:
                            data[key] = value

                # Trigger the event with the specific event type as the state
                _LOGGER.debug("Triggering event: %s with data: %s", event_type, data)
                self._trigger_event(event_type, data)
                self.hass.bus.async_fire(EVENT_LOG, data)

        super()._handle_coordinator_update()
