"""Base entity for Boks."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import BoksDataUpdateCoordinator


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
        # Use centralized device info from coordinator
        info = self.coordinator.device_info.copy()

        # Add connection info
        info["connections"] = {(dr.CONNECTION_BLUETOOTH, self._entry.data[CONF_ADDRESS])}

        return info
