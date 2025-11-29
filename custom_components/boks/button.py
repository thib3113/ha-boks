"""Button platform for Boks."""
import logging
from homeassistant.components import bluetooth
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BoksDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Boks buttons."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BoksSyncLogsButton(coordinator, entry)])

class BoksSyncLogsButton(CoordinatorEntity, ButtonEntity):
    """Representation of a Boks Sync Logs Button."""

    _attr_has_entity_name = True
    _attr_translation_key = "sync_logs"

    def __init__(self, coordinator: BoksDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.data[CONF_MAC]}_sync_logs"

    @property
    def suggested_object_id(self) -> str | None:
        """Return the suggested object id."""
        return "sync_logs"

    @property
    def device_info(self):
        """Return device info."""
        info = {
            "identifiers": {(DOMAIN, self._entry.data[CONF_MAC])},
            "connections": {(dr.CONNECTION_BLUETOOTH, self._entry.data[CONF_MAC])},
            "name": self._entry.data.get(CONF_NAME, "Boks Parcel Box"),
            "manufacturer": "Boks",
            "model": "Boks ONE",
        }
        if self.coordinator.data and "sw_version" in self.coordinator.data:
            info["sw_version"] = self.coordinator.data["sw_version"]
        return info

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.info("Syncing Boks logs...")
        
        try:
            # Use the coordinator's sync method which properly fires events
            await self.coordinator.async_sync_logs(update_state=True)
        except Exception as e:
            _LOGGER.error(f"Failed to sync logs: {e}")
