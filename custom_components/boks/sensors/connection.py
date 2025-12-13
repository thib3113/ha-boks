"""Last connection sensor for Boks."""
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from datetime import datetime

from ..entity import BoksEntity
from ..coordinator import BoksDataUpdateCoordinator


class BoksLastConnectionSensor(BoksEntity, SensorEntity):
    """Representation of a Boks Last Connection Sensor."""

    _attr_translation_key = "last_connection"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

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
