"""Base class for sensors that retain their last valid value."""
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry

from ...coordinator import BoksDataUpdateCoordinator
from ...entity import BoksEntity


class BoksRetainingSensor(BoksEntity, SensorEntity):
    """Base class for sensors that retain their last valid value."""

    def __init__(self, coordinator: BoksDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._last_valid_value: Any = None

    @property
    def native_value(self) -> Any | None:
        """Return the state of the sensor, retaining last valid value if current is None."""
        current_val = self._get_current_value()

        if current_val is not None:
            self._last_valid_value = current_val
            return current_val

        return self._last_valid_value

    def _get_current_value(self) -> Any | None:
        """Get the current value from coordinator data. To be implemented by subclasses."""
        raise NotImplementedError
