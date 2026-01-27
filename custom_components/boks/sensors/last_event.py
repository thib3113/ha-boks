"""Last event sensor for Boks."""

import logging

from homeassistant.components.sensor import (
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from ..coordinator import BoksDataUpdateCoordinator
from ..entity import BoksEntity

_LOGGER = logging.getLogger(__name__)


class BoksLastEventSensor(BoksEntity, SensorEntity, RestoreEntity):
    """Representation of a Boks Last Event Sensor."""

    _attr_translation_key = "last_event"

    def __init__(
        self, coordinator: BoksDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
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
        # We use event_type (e.g. 'code_ble_valid') which maps to translation keys
        event_type = latest_log.get("event_type", "unknown")

        # Update restored state with new value
        self._restored_state = event_type
        return event_type

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        """Return the state attributes."""
        logs = self.coordinator.data.get("latest_logs", [])
        if not logs:
            return {}

        # Get the most recent log
        latest_log = logs[-1] if isinstance(logs, list) and len(logs) > 0 else None
        if not latest_log:
            return {}

        # Process timestamp
        timestamp_val = latest_log.get("timestamp")
        formatted_timestamp = None
        if timestamp_val:
            try:
                # Assuming timestamp is a unix timestamp (seconds)
                dt_obj = dt_util.utc_from_timestamp(timestamp_val)
                # Convert to local time and format as readable string
                formatted_timestamp = dt_util.as_local(dt_obj).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            except Exception:
                formatted_timestamp = str(timestamp_val)

        # Keys that are handled explicitly and should not be duplicated in extras
        standard_keys = {
            "timestamp",
            "event_type",
            "description",
            "opcode",
            "payload",
        }

        # Return detailed information about the last event
        attributes = {
            "timestamp": formatted_timestamp,
            "event_type": latest_log.get("event_type"),
            "description": latest_log.get(
                "description"
            ),  # Description handled by coordinator
            "opcode": latest_log.get("opcode"),
        }

        # Add all other keys from the log as extras (e.g., 'code', 'error_code', etc.)
        for k, v in latest_log.items():
            if k == "extra_data" and isinstance(v, dict):
                for extra_k, extra_v in v.items():
                    if extra_v is not None:
                        attributes[extra_k] = extra_v
            elif k not in standard_keys and v is not None:
                attributes[k] = v

        # Add last 10 events to attributes (Newest First)
        if isinstance(logs, list):
            # Get last 10 events
            last_events_chunk = logs[-10:] if len(logs) >= 10 else logs
            # Reverse them to have Newest -> Oldest
            last_events_reversed = reversed(last_events_chunk)

            # Format events for display
            formatted_events = []
            for log in last_events_reversed:
                # Format timestamp for history
                ts_val = log.get("timestamp")
                ts_str = str(ts_val)
                if ts_val:
                    try:
                        dt_obj = dt_util.utc_from_timestamp(ts_val)
                        ts_str = dt_util.as_local(dt_obj).strftime("%Y-%m-%d %H:%M:%S")
                    except Exception as e:
                        _LOGGER.debug("Error formatting timestamp: %s", e)

                formatted_event = {
                    "timestamp": ts_str,
                    "description": log.get("description"),
                    "event_type": log.get("event_type"),
                }

                # Add extras for this history item
                for k, v in log.items():
                    if k == "extra_data" and isinstance(v, dict):
                        for extra_k, extra_v in v.items():
                            if extra_v is not None:
                                formatted_event[extra_k] = extra_v
                    elif k not in standard_keys and v is not None:
                        formatted_event[k] = v

                formatted_events.append(formatted_event)
            attributes["last_10_events"] = formatted_events

        return attributes
