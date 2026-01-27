"""Last connection sensor for Boks."""
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.helpers.entity import EntityCategory

from ..coordinator import BoksDataUpdateCoordinator
from ..entity import BoksEntity


class BoksLastConnectionSensor(BoksEntity, SensorEntity):
    """Representation of a Boks Last Connection Sensor."""

    _attr_translation_key = "last_connection"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: BoksDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.data[CONF_ADDRESS]}_last_connection"

    @property
    def native_value(self) -> datetime | None:
        """Return the state of the sensor."""
        last_conn = self.coordinator.data.get("last_connection")
        if last_conn:
            return datetime.fromisoformat(last_conn)
        return None
