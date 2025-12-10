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
        self._last_valid_value: float | None = None

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor in Volts (raw/10)."""
        stats = self.coordinator.data.get("battery_stats")
        if stats:
            raw = stats.get(self._key)
            if raw is not None:
                self._last_valid_value = raw / 10.0
                return self._last_valid_value
        
        return self._last_valid_value

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
        self._last_valid_format: str | None = None

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        stats = self.coordinator.data.get("battery_stats")
        if stats:
            fmt = stats.get("format")
            if fmt:
                self._last_valid_format = fmt
                return self._last_valid_format
        
        return self._last_valid_format

    @property
    def suggested_object_id(self) -> str | None:
        """Return the suggested object id."""
        return "battery_format"

class BoksBatteryTypeSensor(BoksEntity, SensorEntity):
    """Representation of the inferred Boks Battery Type."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "battery_type"
    _attr_icon = "mdi:battery-unknown"

    def __init__(self, coordinator: BoksDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.data[CONF_ADDRESS]}_battery_type"
        self._last_valid_type: str | None = None

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        stats = self.coordinator.data.get("battery_stats")
        if stats:
            # We use 'level_mean' or 'level_last' or 'level_single' depending on format
            voltage = None
            if "level_mean" in stats and stats["level_mean"] is not None:
                voltage = stats["level_mean"] / 10.0
            elif "level_last" in stats and stats["level_last"] is not None:
                voltage = stats["level_last"] / 10.0
            elif "level_single" in stats and stats["level_single"] is not None:
                # Single usually is percentage? No, let's assume it might be comparable if available
                # But standard battery service is percentage. Custom is voltage.
                pass
            
            if voltage is not None:
                # Inference Logic
                # LSH20 (or LSH14) is 3.6V nominal.
                # 8x AAA Alkaline is 1.5V * 8 = 12V (series) or 6V (2 sets of 4).
                # Boks typically uses 3.6V Lithium primarily.
                # Let's set a threshold. If > 4.5V, it's likely Alkaline pack.
                if voltage > 4.5:
                    new_type = "8x AAA (Alkaline)"
                else:
                    new_type = "LSH20 (Lithium)"
                
                self._last_valid_type = new_type
                return self._last_valid_type
        
        return self._last_valid_type

    @property
    def suggested_object_id(self) -> str | None:
        """Return the suggested object id."""
        return "battery_type"