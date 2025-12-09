"""Battery diagnostic sensors for Boks."""
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfElectricPotential, CONF_ADDRESS, EntityCategory
from homeassistant.config_entries import ConfigEntry

from ..entity import BoksEntity
from ..coordinator import BoksDataUpdateCoordinator


class BoksBatteryDiagnosticSensor(BoksEntity, SensorEntity):
    """Representation of a Boks Battery Diagnostic Sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_icon = "mdi:current-dc"

    def __init__(self, coordinator: BoksDataUpdateCoordinator, entry: ConfigEntry, key: str) -> None:
        """Initialize the sensor.
        
        Args:
            coordinator: The data update coordinator.
            entry: The config entry.
            key: The key in battery_stats to fetch (e.g. 'level_min').
        """
        super().__init__(coordinator, entry)
        self._key = key
        # Translation key example: battery_level_min
        self._attr_translation_key = f"battery_{key}" 
        self._attr_unique_id = f"{entry.data[CONF_ADDRESS]}_battery_{key}"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor in Volts (raw/10)."""
        stats = self.coordinator.data.get("battery_stats")
        if stats:
            raw = stats.get(self._key)
            if raw is not None:
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

class BoksBatteryFormatSensor(BoksEntity, SensorEntity):
    """Representation of the Boks Battery Measurement Format."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "battery_format"
    _attr_icon = "mdi:ruler"

    def __init__(self, coordinator: BoksDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.data[CONF_ADDRESS]}_battery_format"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        stats = self.coordinator.data.get("battery_stats")
        if stats:
            return stats.get("format")
        return None

    @property
    def suggested_object_id(self) -> str | None:
        """Return the suggested object id."""
        return "battery_format"