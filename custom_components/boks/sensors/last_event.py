"""Last event sensor for Boks."""
from homeassistant.components.sensor import (
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.helpers.restore_state import RestoreEntity

from ..entity import BoksEntity
from ..coordinator import BoksDataUpdateCoordinator


class BoksLastEventSensor(BoksEntity, SensorEntity, RestoreEntity):
    """Representation of a Boks Last Event Sensor."""

    _attr_translation_key = "last_event"

    def __init__(self, coordinator: BoksDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.data[CONF_ADDRESS]}_last_event"
        self._restored_state = None

    @property
    def suggested_object_id(self) -> str | None:
        """Return the suggested object id."""
        return "last_event"

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state:
            self._attr_native_value = state.state
            self._restored_state = state.state

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Call async_write_ha_state to update the entity state
        self.async_write_ha_state()

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        logs = self.coordinator.data.get("latest_logs", [])
        if not logs:
            # Return restored state if no logs and we have a restored state
            if self._restored_state:
                return self._restored_state
            return "no_events"

        # Get the most recent log (logs are sorted with oldest first, so newest is last)
        latest_log = logs[-1] if isinstance(logs, list) and len(logs) > 0 else None
        if not latest_log:
            # Return restored state if no logs and we have a restored state
            if self._restored_state:
                return self._restored_state
            return "no_events"

        # Format the state to be readable
        description = latest_log.get("description", "Unknown Event")
        event_type = latest_log.get("event_type", "unknown")

        # For code-related events, include the code if available
        if event_type in ["code_valid", "code_invalid"] and "code" in latest_log.get("extra_data", {}):
            code = latest_log["extra_data"]["code"]
            return f"{description} ({code})"

        # Update restored state with new value
        self._restored_state = description
        return description

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        """Return the state attributes."""
        logs = self.coordinator.data.get("latest_logs", [])
        if not logs:
            return {}

        # Get the most recent log (logs are sorted with oldest first, so newest is last)
        latest_log = logs[-1] if isinstance(logs, list) and len(logs) > 0 else None
        if not latest_log:
            return {}

        # Return detailed information about the last event
        attributes = {
            "timestamp": latest_log.get("timestamp"),
            "event_type": latest_log.get("event_type"),
            "description": latest_log.get("description"),
            "opcode": latest_log.get("opcode"),
        }

        # Add extra data if available
        if "extra_data" in latest_log and latest_log["extra_data"]:
            attributes.update(latest_log["extra_data"])

        # Add last 10 events to attributes
        if isinstance(logs, list):
            # Get last 10 events, or all if less than 10
            last_10_events = logs[-10:] if len(logs) >= 10 else logs
            # Format events for display
            formatted_events = []
            for log in last_10_events:
                formatted_event = {
                    "timestamp": log.get("timestamp"),
                    "description": log.get("description"),
                    "event_type": log.get("event_type"),
                }
                # Add extra data if available
                if "extra_data" in log and log["extra_data"]:
                    formatted_event.update(log["extra_data"])
                formatted_events.append(formatted_event)
            attributes["last_10_events"] = formatted_events

        return attributes