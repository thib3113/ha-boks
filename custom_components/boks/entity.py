"""Base entity for Boks."""
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers import device_registry as dr
from homeassistant.const import CONF_ADDRESS, CONF_NAME

from .const import DOMAIN
from .coordinator import BoksDataUpdateCoordinator
from homeassistant.config_entries import ConfigEntry


class BoksEntity(CoordinatorEntity):
    """Base class for Boks entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: BoksDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._entry = entry

    @property
    def device_info(self):
        """Return device info."""
        info = {
            "identifiers": {(DOMAIN, self._entry.data[CONF_ADDRESS])},
            "connections": {(dr.CONNECTION_BLUETOOTH, self._entry.data[CONF_ADDRESS])},
            "name": self._entry.data.get(CONF_NAME) or f"Boks {self._entry.data[CONF_ADDRESS]}",
            "manufacturer": "Boks",
            "model": "Boks ONE",
        }
        if self.coordinator.data and "sw_version" in self.coordinator.data:
            info["sw_version"] = self.coordinator.data["sw_version"]
        elif self.coordinator.data and "device_info_service" in self.coordinator.data:
            device_info = self.coordinator.data["device_info_service"]
            if "software_revision" in device_info:
                info["sw_version"] = device_info["software_revision"]
        return info