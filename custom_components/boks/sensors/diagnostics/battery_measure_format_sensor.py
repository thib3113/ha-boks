"""Battery measure format sensor for Boks."""
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import CONF_ADDRESS, EntityCategory
from homeassistant.config_entries import ConfigEntry

from ...coordinator import BoksDataUpdateCoordinator
from .retaining_sensor import BoksRetainingSensor


class BoksBatteryMeasureFormatSensor(BoksRetainingSensor):
    """Representation of a Boks Battery Measure Format Sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["unknown", "measure-single", "measures-t1-t5-t10", "measures-first-min-mean-max-last"]
    _attr_icon = "mdi:battery-heart"

    def __init__(self, coordinator: BoksDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_translation_key = "battery_measure_format"
        self._attr_unique_id = f"{entry.data[CONF_ADDRESS]}_battery_measure_format"

    def _get_current_value(self) -> str | None:
        """Return the current battery measure format from coordinator."""
        stats = self.coordinator.data.get("battery_stats")
        if stats:
            raw = stats.get("measure_format")
            if raw is not None:
                return raw
        return "unknown"

    @property
    def suggested_object_id(self) -> str | None:
        """Return the suggested object id."""
        return "battery_measure_format"