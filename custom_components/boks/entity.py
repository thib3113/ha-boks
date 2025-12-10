"""Base entity for Boks."""
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers import device_registry as dr
from homeassistant.const import CONF_ADDRESS, CONF_NAME

from .const import DOMAIN
from .coordinator import BoksDataUpdateCoordinator
from homeassistant.config_entries import ConfigEntry


from .util import process_device_info

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
        # Get base info using shared utility
        device_info_service = self.coordinator.data.get("device_info_service") if self.coordinator.data else None
        info = process_device_info(self._entry.data, device_info_service)
        
        # Add connection info which is specific to Entity Device Info (not always needed for Registry Update)
        info["connections"] = {(dr.CONNECTION_BLUETOOTH, self._entry.data[CONF_ADDRESS])}
        
        return info