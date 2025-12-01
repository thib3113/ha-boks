"""Code count sensors for Boks."""
from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import CONF_ADDRESS
from homeassistant.config_entries import ConfigEntry

from ..entity import BoksEntity
from ..coordinator import BoksDataUpdateCoordinator


class BoksCodeCountSensor(BoksEntity, SensorEntity):
    """Representation of a Boks Code Count Sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: BoksDataUpdateCoordinator, entry: ConfigEntry, code_type: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._code_type = code_type
        self._attr_translation_key = f"{code_type}_codes_count"
        self._attr_unique_id = f"{entry.data[CONF_ADDRESS]}_{code_type}_codes_count"

    @property
    def suggested_object_id(self) -> str | None:
        """Return the suggested object id."""
        return f"{self._code_type}_codes"

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._code_type, 0)