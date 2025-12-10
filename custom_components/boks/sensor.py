"""Sensor platform for Boks."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .sensors.battery import BoksBatterySensor
from .sensors.battery_temperature import BoksBatteryTemperatureSensor
from .sensors.last_event import BoksLastEventSensor
from .sensors.codes import BoksCodeCountSensor
from .sensors.battery_diagnostics import BoksBatteryDiagnosticSensor, BoksBatteryFormatSensor, BoksBatteryTypeSensor
from .sensors.maintenance import BoksMaintenanceSensor


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Boks sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        BoksBatterySensor(coordinator, entry),
        BoksBatteryTemperatureSensor(coordinator, entry),
        BoksLastEventSensor(coordinator, entry),
        BoksCodeCountSensor(coordinator, entry, "master"),
        BoksCodeCountSensor(coordinator, entry, "single_use"),
        BoksBatteryFormatSensor(coordinator, entry),
        BoksBatteryTypeSensor(coordinator, entry),
        BoksMaintenanceSensor(coordinator, entry),
    ]

    # Check for battery format in coordinator data to selectively add diagnostic sensors
    battery_stats = coordinator.data.get("battery_stats", {})
    battery_format = battery_stats.get("format")

    if battery_format == "measures-first-min-mean-max-last":
        entities.extend([
            BoksBatteryDiagnosticSensor(coordinator, entry, "level_first"),
            BoksBatteryDiagnosticSensor(coordinator, entry, "level_min"),
            BoksBatteryDiagnosticSensor(coordinator, entry, "level_mean"),
            BoksBatteryDiagnosticSensor(coordinator, entry, "level_max"),
            BoksBatteryDiagnosticSensor(coordinator, entry, "level_last"),
        ])
    elif battery_format == "measures-t1-t5-t10":
        entities.extend([
            BoksBatteryDiagnosticSensor(coordinator, entry, "level_t1"),
            BoksBatteryDiagnosticSensor(coordinator, entry, "level_t5"),
            BoksBatteryDiagnosticSensor(coordinator, entry, "level_t10"),
        ])
    
    # If "measure-single" or unknown, we don't add extra diagnostic sensors, 
    # as the main BoksBatterySensor covers the single level.

    async_add_entities(entities)
