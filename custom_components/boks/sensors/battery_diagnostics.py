"""Battery diagnostic sensors for Boks."""
import logging
from typing import Any
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfElectricPotential, CONF_ADDRESS, EntityCategory, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.restore_state import RestoreEntity

from ..entity import BoksEntity
from ..coordinator import BoksDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

class BoksRetainingSensor(BoksEntity, SensorEntity, RestoreEntity):
    """Base class for sensors that retain their last valid value."""

    def __init__(self, coordinator: BoksDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._last_valid_value: Any = None

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        
        if last_state:
            _LOGGER.debug(f"Restoring state for {self.entity_id}: {last_state.state}")
            if last_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                try:
                    if self.device_class == SensorDeviceClass.VOLTAGE:
                        self._last_valid_value = float(last_state.state)
                    else:
                        self._last_valid_value = last_state.state
                    _LOGGER.debug(f"Restored value for {self.entity_id}: {self._last_valid_value}")
                except ValueError:
                    _LOGGER.warning(f"Could not convert restored state '{last_state.state}' for {self.entity_id}")
                    self._last_valid_value = last_state.state
        else:
            _LOGGER.debug(f"No state to restore for {self.entity_id}")

    @property
    def native_value(self) -> Any | None:
        """Return the state of the sensor, retaining last valid value if current is None."""
        current_val = self._get_current_value()
        
        if current_val is not None:
            if current_val != self._last_valid_value:
                 _LOGGER.debug(f"Updating {self.entity_id} with new live value: {current_val}")
            self._last_valid_value = current_val
            return current_val
            
        return self._last_valid_value

    def _get_current_value(self) -> Any | None:
        """Get the current value from coordinator data. To be implemented by subclasses."""
        raise NotImplementedError
from .diagnostics import (
    BoksBatteryDiagnosticSensor,
    BoksBatteryFormatSensor,
    BoksBatteryTypeSensor,
)

__all__ = [
    "BoksBatteryDiagnosticSensor",
    "BoksBatteryFormatSensor",
    "BoksBatteryTypeSensor",
]