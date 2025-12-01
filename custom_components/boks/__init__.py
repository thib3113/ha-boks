"""The Boks integration."""
import importlib
import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, CONF_CONFIG_KEY
from .coordinator import BoksDataUpdateCoordinator

from . import logbook

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.LOCK, Platform.BUTTON, Platform.EVENT, Platform.TODO]

# Service Schemas
SERVICE_ADD_PARCEL_SCHEMA = vol.Schema({
    vol.Optional("description"): cv.string,
})

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

def get_coordinator_from_call(hass: HomeAssistant, call: ServiceCall) -> BoksDataUpdateCoordinator:
    """Retrieve the Boks coordinator from a service call target."""
    # 1. Try Device ID
    device_ids = call.data.get("device_id")
    if device_ids:
        # Normalize to list
        if isinstance(device_ids, str):
            device_ids = [device_ids]

        device_registry = dr.async_get(hass)
        for device_id in device_ids:
            device = device_registry.async_get(device_id)
            if device:
                # Iterate over config entries of the device
                for entry_id in device.config_entries:
                    if entry_id in hass.data[DOMAIN]:
                        return hass.data[DOMAIN][entry_id]

    # 2. Try Entity ID
    entity_ids = call.data.get("entity_id")
    if entity_ids:
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]

        # Retrieve registry to map entity -> config_entry
        from homeassistant.helpers import entity_registry as er
        registry = er.async_get(hass)

        for entity_id in entity_ids:
            entry = registry.async_get(entity_id)
            if entry and entry.config_entry_id in hass.data[DOMAIN]:
                return hass.data[DOMAIN][entry.config_entry_id]

    # 3. Fallback: Single Instance
    if len(hass.data[DOMAIN]) == 1:
        return list(hass.data[DOMAIN].values())[0]

    # 4. Fail
    raise HomeAssistantError("Target Boks device not found or not specified. Please specify a device_id or entity_id.")


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Boks component."""

    # --- Service: Add Parcel ---
    async def handle_add_parcel(call: ServiceCall) -> dict | None:
        """Handle the add parcel service call."""
        description = call.data.get("description", "")

        # Use helper to find coordinator, but for add_parcel we prefer finding the TodoEntity specifically
        # Reuse logic from previous step or adapt get_coordinator?
        # For add_parcel, it specifically needs the TodoEntity to create the item.

        entity_ids = call.data.get("entity_id")

        target_entity_id = None
        if isinstance(entity_ids, list) and len(entity_ids) > 0:
             target_entity_id = entity_ids[0]
        elif isinstance(entity_ids, str):
             target_entity_id = entity_ids

        component = hass.data.get("entity_components", {}).get("todo")
        if not component:
            raise HomeAssistantError("Todo integration not loaded")

        todo_entity = component.get_entity(target_entity_id)

        if not todo_entity:
            # Try to find ANY Boks todo list if not specified (Single device mode)
            if not target_entity_id:
                for entity in component.entities:
                    if hasattr(entity, "platform") and entity.platform.platform_name == DOMAIN:
                        todo_entity = entity
                        break

            if not todo_entity:
                raise HomeAssistantError(f"Target Todo List not found or not specified.")

        # Verify it's a Boks entity
        if not hasattr(todo_entity, "_entry"):
             raise HomeAssistantError(f"Entity {target_entity_id} is not a Boks Parcel List.")

        from homeassistant.components.todo import TodoItem, TodoItemStatus
        import uuid

        new_item = TodoItem(
            uid=uuid.uuid4().hex,
            summary=description,
            status=TodoItemStatus.NEEDS_ACTION,
        )

        await todo_entity.async_create_todo_item(new_item)

        # Try to extract code immediately if possible
        from .parcels.utils import parse_parcel_string
        code_in_desc, _ = parse_parcel_string(description)

        if code_in_desc:
            return {"code": code_in_desc}

        return {"message": "Parcel added, code generation in progress."}

    hass.services.async_register(
        DOMAIN,
        "add_parcel",
        handle_add_parcel,
        schema=SERVICE_ADD_PARCEL_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL
    )

    # --- Service: Add Pin Code ---
    async def handle_add_code(call: ServiceCall) -> dict:
        """Handle the service call."""
        code = call.data.get("code")
        if code:
            code = code.strip().upper()
        code_type = call.data.get("type")
        index = call.data.get("index")

        coordinator = get_coordinator_from_call(hass, call)

        await coordinator.ble_device.connect()
        try:
            created_code = await coordinator.ble_device.create_pin_code(code, code_type, index)
            _LOGGER.info(f"Code {created_code} ({code_type}) added successfully.")
            await coordinator.async_request_refresh()
            return {"code": created_code}
        finally:
            await coordinator.ble_device.disconnect()

    hass.services.async_register(
        DOMAIN,
        "add_pin_code",
        handle_add_code,
        schema=SERVICE_ADD_CODE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL
    )

    # --- Service: Delete Pin Code ---
    async def handle_delete_code(call: ServiceCall):
        """Handle the service call."""
        identifier = call.data.get("identifier")
        if identifier:
            identifier = identifier.strip().upper()
        code_type = call.data.get("type")

        coordinator = get_coordinator_from_call(hass, call)

        await coordinator.ble_device.connect()
        try:
            await coordinator.ble_device.delete_pin_code(code_type, identifier)
            _LOGGER.info(f"Code {identifier} ({code_type}) deleted successfully.")
            await coordinator.async_request_refresh()
        finally:
            await coordinator.ble_device.disconnect()

    hass.services.async_register(
        DOMAIN,
        "delete_pin_code",
        handle_delete_code,
        schema=SERVICE_DELETE_CODE_SCHEMA
    )

    # --- Service: Sync Logs ---
    async def handle_sync_logs(call: ServiceCall):
        """Handle the sync logs service call."""
        coordinator = get_coordinator_from_call(hass, call)
        _LOGGER.info("Manual log sync requested via service")

        try:
            await coordinator.async_sync_logs(update_state=True)
        except Exception as e:
            _LOGGER.error(f"Failed to sync logs via service: {e}")
            raise

    hass.services.async_register(
        DOMAIN,
        "sync_logs",
        handle_sync_logs,
        schema=SERVICE_SYNC_LOGS_SCHEMA
    )

    return True

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
