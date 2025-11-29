"""The Boks integration."""
import importlib
import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import DOMAIN
from .coordinator import BoksDataUpdateCoordinator

from . import logbook

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.LOCK, Platform.BUTTON, Platform.EVENT, Platform.TODO]

# Service Schemas
SERVICE_ADD_CODE_SCHEMA = vol.Schema({
    vol.Optional("code"): cv.string,
    vol.Optional("type", default="standard"): vol.In(["standard", "master", "single", "multi"]),
    vol.Optional("index", default=0): cv.positive_int,
})

SERVICE_DELETE_CODE_SCHEMA = vol.Schema({
    vol.Required("identifier"): cv.string, # Code itself or Index
    vol.Optional("type", default="standard"): vol.In(["standard", "master", "single", "multi"]),
})

SERVICE_SYNC_LOGS_SCHEMA = vol.Schema({})

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Boks from a config entry."""

    coordinator = BoksDataUpdateCoordinator(hass, entry)

    try:
        await coordinator.async_config_entry_first_refresh()
    except UpdateFailed as ex:
        raise ConfigEntryNotReady(f"Coordinator init failed: {ex}") from ex

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Pre-import platforms to avoid blocking call in the loop
    for platform in PLATFORMS:
        await hass.async_add_executor_job(
            importlib.import_module, f".{platform}", __package__
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    # Register Services
    async def handle_add_code(call: ServiceCall) -> dict:
        """Handle the service call."""
        code = call.data.get("code")
        if code:
            code = code.strip().upper()
        code_type = call.data.get("type")
        index = call.data.get("index")

        coordinator = list(hass.data[DOMAIN].values())[0]

        # Use the new BoksBluetoothDevice methods
        await coordinator.ble_device.connect()
        try:
            created_code = await coordinator.ble_device.create_pin_code(code, code_type, index)
            _LOGGER.info(f"Code {created_code} ({code_type}) added successfully.")
            await coordinator.async_request_refresh()
            return {"code": created_code}
        finally:
            await coordinator.ble_device.disconnect()

    async def handle_delete_code(call: ServiceCall):
        """Handle the service call."""
        identifier = call.data.get("identifier")
        if identifier:
            identifier = identifier.strip().upper()
        code_type = call.data.get("type")

        coordinator = list(hass.data[DOMAIN].values())[0]

        await coordinator.ble_device.connect()
        try:
            await coordinator.ble_device.delete_pin_code(code_type, identifier)
            _LOGGER.info(f"Code {identifier} ({code_type}) deleted successfully.")
            await coordinator.async_request_refresh()
        finally:
            await coordinator.ble_device.disconnect()

    async def handle_sync_logs(call: ServiceCall):
        """Handle the sync logs service call."""
        coordinator = list(hass.data[DOMAIN].values())[0]
        _LOGGER.info("Manual log sync requested via service")

        try:
            # Use the coordinator's sync method which properly fires events
            await coordinator.async_sync_logs(update_state=True)
        except Exception as e:
            _LOGGER.error(f"Failed to sync logs via service: {e}")
            raise

    hass.services.async_register(
        DOMAIN,
        "add_pin_code",
        handle_add_code,
        schema=SERVICE_ADD_CODE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL
    )

    hass.services.async_register(
        DOMAIN,
        "delete_pin_code",
        handle_delete_code,
        schema=SERVICE_DELETE_CODE_SCHEMA
    )

    hass.services.async_register(
        DOMAIN,
        "sync_logs",
        handle_sync_logs,
        schema=SERVICE_SYNC_LOGS_SCHEMA
    )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""

    # Check if master code has changed
    new_master_code = entry.options.get("master_code")

    if new_master_code:
        new_master_code = new_master_code.strip().upper()
        _LOGGER.info(f"Master code change requested for {entry.title}. New code: {new_master_code}")

        # Update the config entry data with the new master code directly, without BLE interaction
        new_data = dict(entry.data)
        new_data["master_code"] = new_master_code
        hass.config_entries.async_update_entry(entry, data=new_data)
        _LOGGER.info(f"Master code updated successfully in configuration to {new_master_code}.")

        # Clear the option to avoid re-triggering on next reload if not intended
        new_options = dict(entry.options)
        if "master_code" in new_options:
            del new_options["master_code"]

        hass.config_entries.async_update_entry(
            entry,
            options=new_options
        )

    await hass.config_entries.async_reload(entry.entry_id)
