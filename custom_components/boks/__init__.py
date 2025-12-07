"""The Boks integration."""
import importlib
import logging
import voluptuous as vol
import json
import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, CONF_CONFIG_KEY
from .coordinator import BoksDataUpdateCoordinator

from . import logbook

# Define the CONFIG_SCHEMA as an empty schema for config entries only
CONFIG_SCHEMA = vol.Schema({}, extra=vol.ALLOW_EXTRA)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.LOCK, Platform.BUTTON, Platform.EVENT, Platform.TODO]

# Service Schemas
SERVICE_ADD_PARCEL_SCHEMA = vol.Schema({
    vol.Optional("description"): cv.string,
}, extra=vol.ALLOW_EXTRA)

SERVICE_ADD_CODE_SCHEMA = vol.Schema({
    vol.Optional("code"): cv.string,
    vol.Optional("type", default="standard"): vol.In(["standard", "master", "single", "multi"]),
    vol.Optional("index", default=0): cv.positive_int,
}, extra=vol.ALLOW_EXTRA)

SERVICE_DELETE_CODE_SCHEMA = vol.Schema({
    vol.Required("identifier"): cv.string, # Code itself or Index
    vol.Optional("type", default="standard"): vol.In(["standard", "master", "single", "multi"]),
}, extra=vol.ALLOW_EXTRA)

SERVICE_SYNC_LOGS_SCHEMA = vol.Schema({}, extra=vol.ALLOW_EXTRA)

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

        # If device_ids were provided but we didn't return above, it means none were Boks devices
        raise HomeAssistantError(f"Target device(s) {device_ids} are not Boks devices.")

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

        # If entity_ids were provided but we didn't return above, none were Boks entities
        raise HomeAssistantError(f"Target entity(s) {entity_ids} belong to non-Boks devices.")

    # 3. Fallback: Single Instance (Only if NO target was provided)
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

        target_entity_id = None

        # 1. Extract Target (Entity ID) from call.data (populated by HA from target)
        if "entity_id" in call.data:
            entity_ids = call.data["entity_id"]
            if isinstance(entity_ids, list) and len(entity_ids) > 0:
                 target_entity_id = entity_ids[0]
            elif isinstance(entity_ids, str):
                 target_entity_id = entity_ids

        # 2. Fallback (Single Instance)
        if not target_entity_id:
            # Check how many Boks entries are loaded
            boks_entry_ids = list(hass.data[DOMAIN].keys())
            if len(boks_entry_ids) == 1:
                config_entry_id = boks_entry_ids[0]
                # Find Todo entity
                entity_registry = er.async_get(hass)
                entries = entity_registry.entities.values()
                for entry in entries:
                    if entry.config_entry_id == config_entry_id and entry.domain == "todo":
                        target_entity_id = entry.entity_id
                        break
            elif len(boks_entry_ids) > 1:
                 raise HomeAssistantError("Multiple Boks devices found. Please specify a target entity.")
            else:
                 raise HomeAssistantError("No Boks devices configured.")

        if not target_entity_id:
             raise HomeAssistantError("Could not resolve a target Boks Todo list.")

        # 3. Get Actual Entity Object
        component = hass.data.get("entity_components", {}).get("todo")
        if not component:
             raise HomeAssistantError("Todo integration not loaded.")

        todo_entity = component.get_entity(target_entity_id)

        if not todo_entity:
             raise HomeAssistantError(f"Todo entity '{target_entity_id}' not found or not loaded.")

        # 4. Verify it's a Boks entity
        from .todo import BoksParcelTodoList
        if not isinstance(todo_entity, BoksParcelTodoList):
             raise HomeAssistantError(f"Entity {target_entity_id} is not a Boks Parcel List.")

        # 5. Generate/Parse Code and Create Parcel
        from .parcels.utils import parse_parcel_string, generate_random_code, format_parcel_item

        # Check if we have a config key for BLE operations
        has_config_key = getattr(todo_entity, "_has_config_key", False)

        # Try to extract code immediately if possible, otherwise generate one
        code_in_desc, parsed_description = parse_parcel_string(description)
        generated_code = None
        force_sync = False

        if not code_in_desc:
            generated_code = generate_random_code()

            if has_config_key:
                # If we have a key, we want to force a sync because we just generated this code
                # and the user expects it to be created on the device.
                force_sync = True

            formatted_description = format_parcel_item(generated_code, description or "Parcel")
        else:
            formatted_description = description
            generated_code = code_in_desc
            # If code was provided, we normally track only.
            # But if the user explicitly called this service, maybe they want to force sync?
            # For now, stick to "Manual input = Tracking" UNLESS we generated it.
            force_sync = False

        # Delegate creation to the Todo Entity's specialized method
        # We use force_background_sync=True if we generated the code and want it synced.
        await todo_entity.async_create_parcel(formatted_description, force_background_sync=force_sync)

        return {"code": generated_code}

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

    # Cache translations for Logbook usage (Manual Load)
    try:
        lang = hass.config.language
        # Path to the integration directory
        integration_path = os.path.dirname(__file__)
        translation_path = os.path.join(integration_path, "translations", f"{lang}.json")

        # Fallback to English if file doesn't exist
        if not os.path.exists(translation_path):
            _LOGGER.warning("Translation file for '%s' not found at %s, falling back to 'en'", lang, translation_path)
            translation_path = os.path.join(integration_path, "translations", "en.json")

        if os.path.exists(translation_path):
            def load_json(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)

            # Execute file I/O in executor to avoid blocking event loop
            translations_json = await hass.async_add_executor_job(load_json, translation_path)

            # Extract the specific state translations we need
            # Structure: entity -> sensor -> last_event -> state
            try:
                state_translations = translations_json.get("entity", {}).get("sensor", {}).get("last_event", {}).get("state", {})
                hass.data[DOMAIN]["translations"] = state_translations
                _LOGGER.debug("Manually loaded translations for Logbook: %s", list(state_translations.keys()))
            except AttributeError:
                hass.data[DOMAIN]["translations"] = {}
                _LOGGER.warning("Could not extract state translations from JSON structure")
        else:
             hass.data[DOMAIN]["translations"] = {}
             _LOGGER.warning("No translation file found at %s (fallback failed)", translation_path)

    except Exception as e:
        _LOGGER.warning("Failed to manually load translations for Logbook: %s", e)
        hass.data[DOMAIN]["translations"] = {}

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
