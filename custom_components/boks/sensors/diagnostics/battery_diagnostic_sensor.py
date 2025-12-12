"""Battery diagnostic sensor for Boks."""
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfElectricPotential, CONF_ADDRESS, EntityCategory
from homeassistant.config_entries import ConfigEntry

from ...coordinator import BoksDataUpdateCoordinator
from .retaining_sensor import BoksRetainingSensor


class BoksBatteryDiagnosticSensor(BoksRetainingSensor):
    """Representation of a Boks Battery Diagnostic Sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_icon = "mdi:current-dc"

    def __init__(self, coordinator: BoksDataUpdateCoordinator, entry: ConfigEntry, key: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._key = key
        self._attr_translation_key = f"battery_{key}"
        self._attr_unique_id = f"{entry.data[CONF_ADDRESS]}_battery_{key}"

    def _get_current_value(self) -> float | None:
        """Return the current voltage from coordinator."""
        stats = self.coordinator.data.get("battery_stats")
        if stats:
            # Check if this sensor's key is relevant for the current battery format
            battery_format = stats.get("format")
            
            # Define which keys are relevant for each format
            format_keys = {
                "measure-single": ["level_single"],
                "measures-t1-t5-t10": ["level_t1", "level_t5", "level_t10"],
                "measures-first-min-mean-max-last": ["level_first", "level_min", "level_mean", "level_max", "level_last"]
            }
            
            # If we have a format and this key is not relevant for that format, return None
            if battery_format and battery_format in format_keys:
                if self._key not in format_keys[battery_format] and self._key != "temperature":
                    return None
            
            raw = stats.get(self._key)
            if raw is not None:
                # For temperature, return as-is (already converted)
                if self._key == "temperature":
                    return float(raw)
                # For voltage levels, convert from raw value
                return raw / 10.0
        return None

    @property
    def suggested_object_id(self) -> str | None:
        """Return the suggested object id."""
        return f"battery_{self._key}"

    @property
    def suggested_display_precision(self) -> int:
        """Return the suggested display precision."""
        return 1

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Check if this sensor is relevant for the current battery format
        stats = self.coordinator.data.get("battery_stats")
        if stats:
            battery_format = stats.get("format")
            
            # Define which keys are relevant for each format
            format_keys = {
                "measure-single": ["level_single"],
                "measures-t1-t5-t10": ["level_t1", "level_t5", "level_t10"],
                "measures-first-min-mean-max-last": ["level_first", "level_min", "level_mean", "level_max", "level_last"]
            }
            
            # If we have a format and this key is not relevant for that format, mark as unavailable
            if battery_format and battery_format in format_keys:
                return self._key in format_keys[battery_format] or self._key == "temperature"
            
            # If we don't have a format yet, assume all sensors could be relevant
            return True
            
        # If we don't have stats at all, mark as unavailable
        return False