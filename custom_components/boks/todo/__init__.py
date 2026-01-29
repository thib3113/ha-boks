import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import CONF_CONFIG_KEY, DOMAIN
from ..coordinator import BoksDataUpdateCoordinator
from .entity import BoksParcelTodoList
from .storage import BoksParcelStore

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Boks todo list."""
    coordinator: BoksDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Initialize the store
    store = BoksParcelStore(hass, entry.entry_id)
    await store.load()

    # Check if config key is present for BLE sync operations
    has_config_key = bool(entry.data.get(CONF_CONFIG_KEY))
    if not has_config_key:
        _LOGGER.info("Boks Config Key missing: Parcel Todo List will run in tracking-only mode (no code sync to Boks).")

    entity = BoksParcelTodoList(coordinator, entry, store, has_config_key)
    async_add_entities([entity])
