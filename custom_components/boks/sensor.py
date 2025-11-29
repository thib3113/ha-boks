"""Sensor platform for Boks."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .sensors.battery import BoksBatterySensor
from .sensors.last_event import BoksLastEventSensor
from .sensors.codes import BoksCodeCountSensor


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Boks sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        BoksBatterySensor(coordinator, entry),
        BoksLastEventSensor(coordinator, entry),
        BoksCodeCountSensor(coordinator, entry, "master"),
        BoksCodeCountSensor(coordinator, entry, "single_use")
    ]

    async_add_entities(entities)
