"""Battery temperature sensor for Boks."""
import logging
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
    EntityCategory,
)
from homeassistant.const import UnitOfTemperature, CONF_ADDRESS
from homeassistant.config_entries import ConfigEntry

from ..entity import BoksEntity
from ..coordinator import BoksDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

class BoksBatteryTemperatureSensor(BoksEntity, SensorEntity):
    """Representation of a Boks Battery Temperature Sensor."""

    _attr_translation_key = "battery_temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: BoksDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.data[CONF_ADDRESS]}_battery_temperature"
        self._last_valid_temperature: int | None = None # Store last valid temperature

    @property
    def suggested_object_id(self) -> str | None:
        """Return the suggested object id."""
        return "battery_temperature"

    @property
    def native_value(self) -> int | None: # Changed return type to allow None initially
        """Return the state of the sensor."""
        current_temp = self.coordinator.data.get("battery_temperature") # Get value without default
        
        # Check for invalid temperature (255 or None)
        if current_temp is None or current_temp == 255:
            _LOGGER.debug("Invalid temperature reading (255 or None) for %s. Returning last valid: %s", self.entity_id, self._last_valid_temperature)
            return self._last_valid_temperature

        
        # Update and return valid temperature
        self._last_valid_temperature = current_temp
        return current_temp