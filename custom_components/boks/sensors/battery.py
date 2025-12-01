"""Battery sensor for Boks."""
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, CONF_ADDRESS
from homeassistant.config_entries import ConfigEntry

from ..entity import BoksEntity
from ..coordinator import BoksDataUpdateCoordinator


class BoksBatterySensor(BoksEntity, SensorEntity):
    """Representation of a Boks Battery Sensor."""

    _attr_translation_key = "battery"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator: BoksDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.data[CONF_ADDRESS]}_battery"

    @property
    def suggested_object_id(self) -> str | None:
        """Return the suggested object id."""
        return "battery"

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self.coordinator.data.get("battery_level", 0)