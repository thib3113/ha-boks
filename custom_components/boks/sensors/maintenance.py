from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.helpers.entity import EntityCategory

from ..coordinator import BoksDataUpdateCoordinator
from ..entity import BoksEntity


class BoksMaintenanceSensor(BoksEntity, SensorEntity):
    """Sensor to track maintenance operations status."""

    _attr_has_entity_name = True
    _attr_translation_key = "maintenance_status"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:broom"

    def __init__(self, coordinator: BoksDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._entry = entry
        self._attr_unique_id = f"{entry.data[CONF_ADDRESS]}_maintenance_status"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        status = self.coordinator.maintenance_status
        if not status or not status.get("running"):
            return "idle"

        current = status.get("current_index", 0)
        total = status.get("total_to_clean", 0)
        percent = int((current / total) * 100) if total > 0 else 0

        return "cleaning"

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return extra attributes."""
        status = self.coordinator.maintenance_status
        if not status:
            return None

        return {
            "running": status.get("running", False),
            "current_index": status.get("current_index"),
            "target_range": status.get("total_to_clean"),
            "progress_percent": status.get("progress", 0),
            "last_cleaned_index": status.get("last_cleaned"),
            "message": status.get("message", "")
        }
