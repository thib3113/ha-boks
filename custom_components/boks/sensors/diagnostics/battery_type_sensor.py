"""Battery type sensor for Boks."""
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import CONF_ADDRESS, EntityCategory
from homeassistant.config_entries import ConfigEntry

from ...coordinator import BoksDataUpdateCoordinator
from .retaining_sensor import BoksRetainingSensor
from ...const import PCB_VERSIONS


class BoksBatteryTypeSensor(BoksRetainingSensor):
    """Representation of a Boks Battery Type Sensor (Physical Type)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["unknown", "lsh14", "8x_aaa", "other"]
    _attr_icon = "mdi:battery-unknown"

    def __init__(self, coordinator: BoksDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_translation_key = "battery_type"
        self._attr_unique_id = f"{entry.data[CONF_ADDRESS]}_battery_type"

    def _get_current_value(self) -> str | None:
        """Return the current battery type from coordinator."""
        # Infer from PCB Version
        device_info = self.coordinator.data.get("device_info_service", {})
        fw_rev = device_info.get("firmware_revision")
        
        if fw_rev and fw_rev in PCB_VERSIONS:
            pcb_version = PCB_VERSIONS[fw_rev]
            if pcb_version == "3.0":
                return "lsh14"
            elif pcb_version == "4.0":
                return "8x_aaa"

        return "unknown"

    @property
    def suggested_object_id(self) -> str | None:
        """Return the suggested object id."""
        return "battery_type"