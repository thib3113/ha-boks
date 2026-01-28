"""Battery diagnostic sensors for Boks."""
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import StateType

from ..coordinator import BoksDataUpdateCoordinator
from ..entity import BoksEntity
from .diagnostics import (
    BoksBatteryDiagnosticSensor,
    BoksBatteryFormatSensor,
    BoksBatteryTypeSensor,
)

_LOGGER = logging.getLogger(__name__)

class BoksRetainingSensor(BoksEntity, SensorEntity, RestoreEntity):
    """Base class for sensors that retain their last valid value."""

    def __init__(self, coordinator: BoksDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._last_valid_value: Any = None
        self._data_key: str | None = None

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in ("unknown", "unavailable"):
            _LOGGER.debug("Restoring state for %s: %s", self.entity_id, last_state.state)
            try:
                if self._attr_device_class == SensorDeviceClass.VOLTAGE:
                    self._last_valid_value = float(last_state.state)
                else:
                    self._last_valid_value = int(last_state.state)
                _LOGGER.debug("Restored value for %s: %s", self.entity_id, self._last_valid_value)
            except ValueError:
                _LOGGER.warning("Could not convert restored state '%s' for %s", last_state.state, self.entity_id)
        else:
            _LOGGER.debug("No state to restore for %s", self.entity_id)

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if not self._data_key:
            return self._last_valid_value

        current_val = self.coordinator.data.get(self._data_key)

        # If we have a new live value, update last_valid and return it
        if current_val is not None:
            _LOGGER.debug("Updating %s with new live value: %s", self.entity_id, current_val)
            self._last_valid_value = current_val
            return current_val
        
        return self._last_valid_value

    def _get_current_value(self) -> Any | None:
        """Get the current value from coordinator data. To be implemented by subclasses."""
        raise NotImplementedError

__all__ = [
    "BoksBatteryDiagnosticSensor",
    "BoksBatteryFormatSensor",
    "BoksBatteryTypeSensor",
]
