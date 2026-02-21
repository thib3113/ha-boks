"Services for the Boks integration."
import logging

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, MAX_MASTER_CODE_CLEAN_RANGE
from .coordinator import BoksDataUpdateCoordinator
from .errors import BoksError

_LOGGER = logging.getLogger(__name__)

# --- Service Schemas ---

SERVICE_ADD_PARCEL_SCHEMA = vol.Schema({
    vol.Optional("description"): cv.string,
}, extra=vol.ALLOW_EXTRA)

SERVICE_OPEN_DOOR_SCHEMA = vol.Schema({
    vol.Optional("code"): cv.string,
}, extra=vol.ALLOW_EXTRA)

SERVICE_ADD_MASTER_CODE_SCHEMA = vol.Schema({
    vol.Required("code"): cv.string,
    vol.Required("index"): vol.All(vol.Coerce(int), vol.Range(min=0)),
}, extra=vol.ALLOW_EXTRA)

SERVICE_DELETE_MASTER_CODE_SCHEMA = vol.Schema({
    vol.Required("index"): vol.All(vol.Coerce(int), vol.Range(min=0)),
}, extra=vol.ALLOW_EXTRA)

SERVICE_ADD_SINGLE_CODE_SCHEMA = vol.Schema({
    vol.Required("code"): cv.string,
}, extra=vol.ALLOW_EXTRA)

SERVICE_DELETE_SINGLE_CODE_SCHEMA = vol.Schema({
    vol.Required("code"): cv.string,
}, extra=vol.ALLOW_EXTRA)

SERVICE_ADD_MULTI_CODE_SCHEMA = vol.Schema({
    vol.Required("code"): cv.string,
}, extra=vol.ALLOW_EXTRA)

SERVICE_DELETE_MULTI_CODE_SCHEMA = vol.Schema({
    vol.Required("code"): cv.string,
}, extra=vol.ALLOW_EXTRA)

SERVICE_SYNC_LOGS_SCHEMA = vol.Schema({}, extra=vol.ALLOW_EXTRA)

SERVICE_CLEAN_MASTER_CODES_SCHEMA = vol.Schema({
    vol.Optional("start_index", default=0): cv.positive_int,
    vol.Optional("range", default=MAX_MASTER_CODE_CLEAN_RANGE): cv.positive_int,
}, extra=vol.ALLOW_EXTRA)

SERVICE_SET_CONFIGURATION_SCHEMA = vol.Schema({
    vol.Optional("laposte"): cv.boolean,
}, extra=vol.ALLOW_EXTRA)

SERVICE_NFC_SCAN_START_SCHEMA = vol.Schema({}, extra=vol.ALLOW_EXTRA)

SERVICE_NFC_REGISTER_TAG_SCHEMA = vol.Schema({
    vol.Required("uid"): cv.string,
    vol.Optional("name"): cv.string,
}, extra=vol.ALLOW_EXTRA)

SERVICE_NFC_UNREGISTER_TAG_SCHEMA = vol.Schema({
    vol.Required("uid"): cv.string,
}, extra=vol.ALLOW_EXTRA)

SERVICE_GENERATE_UPDATE_PACKAGE_SCHEMA = vol.Schema({
    vol.Required("version"): cv.string,
}, extra=vol.ALLOW_EXTRA)


def get_coordinator_from_call(hass: HomeAssistant, call: ServiceCall) -> BoksDataUpdateCoordinator:
    """Retrieve the Boks coordinator from a service call target."""
    # 1. Try Device ID
    if "device_id" in call.data:
        coord = _get_coordinator_by_device_id(hass, call.data["device_id"])
        if coord:
            return coord

    # 2. Try Entity ID
    if "entity_id" in call.data:
        coord = _get_coordinator_by_entity_id(hass, call.data["entity_id"])
        if coord:
            return coord

    # 3. Fallback: Single Instance (Only if NO target was provided)
    coords = [v for v in hass.data.get(DOMAIN, {}).values() if isinstance(v, BoksDataUpdateCoordinator)]
    if len(coords) == 1:
        return coords[0]

    # 4. Fail
    raise HomeAssistantError(
        translation_domain=DOMAIN,
        translation_key="target_device_missing"
    )


def _get_coordinator_by_device_id(hass: HomeAssistant, device_ids: str | list[str]) -> BoksDataUpdateCoordinator | None:
    """Resolve coordinator from device IDs."""
    if isinstance(device_ids, str):
        device_ids = [device_ids]

    device_registry = dr.async_get(hass)
    for device_id in device_ids:
        device = device_registry.async_get(device_id)
        if device:
            for entry_id in device.config_entries:
                # 1. Try loaded coordinator
                if entry_id in hass.data.get(DOMAIN, {}):
                    return hass.data[DOMAIN][entry_id]

                # 2. Fallback: Create temp coordinator if entry exists but not loaded
                config_entry = hass.config_entries.async_get_entry(entry_id)
                if config_entry and config_entry.domain == DOMAIN:
                    _LOGGER.debug("Integration not loaded for device %s, creating temporary coordinator", device_id)
                    coord = BoksDataUpdateCoordinator(hass, config_entry)
                    coord.update_interval = None # Disable background polling leaks
                    return coord

    raise HomeAssistantError(
        translation_domain=DOMAIN,
        translation_key="target_devices_not_boks",
        translation_placeholders={"device_ids": str(device_ids)}
    )


def _get_coordinator_by_entity_id(hass: HomeAssistant, entity_ids: str | list[str]) -> BoksDataUpdateCoordinator | None:
    """Resolve coordinator from entity IDs."""
    if isinstance(entity_ids, str):
        entity_ids = [entity_ids]

    registry = er.async_get(hass)
    for entity_id in entity_ids:
        entry = registry.async_get(entity_id)
        if entry:
            # 1. Try loaded coordinator
            if entry.config_entry_id in hass.data.get(DOMAIN, {}):
                return hass.data[DOMAIN][entry.config_entry_id]

            # 2. Fallback: Create temp coordinator if entry exists but not loaded
            config_entry = hass.config_entries.async_get_entry(entry.config_entry_id)
            if config_entry and config_entry.domain == DOMAIN:
                _LOGGER.debug("Integration not loaded for entity %s, creating temporary coordinator", entity_id)
                coord = BoksDataUpdateCoordinator(hass, config_entry)
                coord.update_interval = None # Disable background polling leaks
                return coord

    raise HomeAssistantError(
        translation_domain=DOMAIN,
        translation_key="target_entities_not_boks",
        translation_placeholders={"entity_ids": str(entity_ids)}
    )



SERVICE_DELETE_UPDATE_PACKAGE_SCHEMA = vol.Schema({vol.Required("version"): cv.string})

SERVICE_GENERATE_PIN_CODE_SCHEMA = vol.Schema({
    vol.Required("type"): vol.In(["master", "single", "multi"]),
    vol.Required("index"): vol.All(vol.Coerce(int), vol.Range(min=0)),
}, extra=vol.ALLOW_EXTRA)

async def async_setup_services(hass: HomeAssistant):
    """Register services for the Boks integration."""

    # --- Service: Open Door ---
    async def handle_open_door(call: ServiceCall):
        """Handle the open door service call."""
        coordinator = get_coordinator_from_call(hass, call)
        await coordinator.commands.open_door(call.data.get("code"))

    hass.services.async_register(
        DOMAIN,
        "open_door",
        handle_open_door,
        schema=SERVICE_OPEN_DOOR_SCHEMA
    )

    # --- Service: Add Parcel ---
    async def handle_add_parcel(call: ServiceCall) -> dict | None:
        """Handle the add parcel service call."""
        coordinator = get_coordinator_from_call(hass, call)

        # Resolve optional entity/device targeting from service call
        entity_id = None
        device_id = None

        if "entity_id" in call.data:
            e_ids = call.data["entity_id"]
            if isinstance(e_ids, list) and len(e_ids) > 0:
                entity_id = e_ids[0]
            elif isinstance(e_ids, str):
                entity_id = e_ids

        if "device_id" in call.data:
            d_ids = call.data["device_id"]
            if isinstance(d_ids, list) and len(d_ids) > 0:
                device_id = d_ids[0]
            elif isinstance(d_ids, str):
                device_id = d_ids

        return await coordinator.parcels.add_parcel(
            description=call.data.get("description", ""),
            entity_id=entity_id,
            device_id=device_id
        )

    hass.services.async_register(
        DOMAIN,
        "add_parcel",
        handle_add_parcel,
        schema=SERVICE_ADD_PARCEL_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL
    )

    # --- Service: Add Master Code ---
    async def handle_add_master_code(call: ServiceCall):
        coordinator = get_coordinator_from_call(hass, call)
        return await coordinator.codes.create_code(call.data["code"], "master", call.data["index"])

    hass.services.async_register(
        DOMAIN,
        "add_master_code",
        handle_add_master_code,
        schema=SERVICE_ADD_MASTER_CODE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL
    )

    # --- Service: Delete Master Code ---
    async def handle_delete_master_code(call: ServiceCall):
        coordinator = get_coordinator_from_call(hass, call)
        return await coordinator.codes.delete_code("master", call.data["index"])

    hass.services.async_register(
        DOMAIN,
        "delete_master_code",
        handle_delete_master_code,
        schema=SERVICE_DELETE_MASTER_CODE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL
    )

    # --- Service: Add Single Code ---
    async def handle_add_single_code(call: ServiceCall):
        coordinator = get_coordinator_from_call(hass, call)
        return await coordinator.codes.create_code(call.data["code"], "single")

    hass.services.async_register(
        DOMAIN,
        "add_single_code",
        handle_add_single_code,
        schema=SERVICE_ADD_SINGLE_CODE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL
    )

    # --- Service: Delete Single Code ---
    async def handle_delete_single_code(call: ServiceCall):
        coordinator = get_coordinator_from_call(hass, call)
        return await coordinator.codes.delete_code("single", call.data["code"])

    hass.services.async_register(
        DOMAIN,
        "delete_single_code",
        handle_delete_single_code,
        schema=SERVICE_DELETE_SINGLE_CODE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL
    )

    # --- Service: Add Multi Code ---
    async def handle_add_multi_code(call: ServiceCall):
        coordinator = get_coordinator_from_call(hass, call)
        return await coordinator.codes.create_code(call.data["code"], "multi")

    hass.services.async_register(
        DOMAIN,
        "add_multi_code",
        handle_add_multi_code,
        schema=SERVICE_ADD_MULTI_CODE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL
    )

    # --- Service: Delete Multi Code ---
    async def handle_delete_multi_code(call: ServiceCall):
        coordinator = get_coordinator_from_call(hass, call)
        return await coordinator.codes.delete_code("multi", call.data["code"])

    hass.services.async_register(
        DOMAIN,
        "delete_multi_code",
        handle_delete_multi_code,
        schema=SERVICE_DELETE_MULTI_CODE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL
    )

    # --- Service: Sync Logs ---
    async def handle_sync_logs(call: ServiceCall):
        """Handle the sync logs service call."""
        coordinator = get_coordinator_from_call(hass, call)
        await coordinator.commands.sync_logs()

    hass.services.async_register(
        DOMAIN,
        "sync_logs",
        handle_sync_logs,
        schema=SERVICE_SYNC_LOGS_SCHEMA
    )

    # --- Service: Clean Master Codes ---
    async def handle_clean_master_codes(call: ServiceCall):
        """Handle the clean master codes service call."""
        start_index = call.data.get("start_index", 0)
        range_val = call.data.get("range", MAX_MASTER_CODE_CLEAN_RANGE)

        coordinator = get_coordinator_from_call(hass, call)
        await coordinator.codes.clean_master_codes(start_index, range_val)

    hass.services.async_register(
        DOMAIN,
        "clean_master_codes",
        handle_clean_master_codes,
        schema=SERVICE_CLEAN_MASTER_CODES_SCHEMA
    )

    # --- Service: Set Configuration ---
    async def handle_set_configuration(call: ServiceCall):
        """Handle the set configuration service call."""
        coordinator = get_coordinator_from_call(hass, call)
        await coordinator.commands.set_configuration(call.data.get("laposte"))

    hass.services.async_register(
        DOMAIN,
        "set_configuration",
        handle_set_configuration,
        schema=SERVICE_SET_CONFIGURATION_SCHEMA
    )

    # --- Service: Start NFC Scan ---
    async def handle_nfc_scan_start(call: ServiceCall):
        """Handle NFC Scan Start."""
        coordinator = get_coordinator_from_call(hass, call)
        try:
            await coordinator.nfc.start_scan()
        except BoksError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=e.translation_key,
                translation_placeholders=e.translation_placeholders
            ) from e
        except Exception as e:
            _LOGGER.error("Error starting NFC scan: %s", e)
            raise HomeAssistantError(f"Unexpected error: {e}") from e

    hass.services.async_register(
        DOMAIN,
        "nfc_scan_start",
        handle_nfc_scan_start,
        schema=SERVICE_NFC_SCAN_START_SCHEMA
    )

    # --- Service: Register NFC Tag ---
    async def handle_nfc_register_tag(call: ServiceCall):
        """Handle registering an NFC tag."""
        uid = call.data["uid"]
        name = call.data.get("name")
        coordinator = get_coordinator_from_call(hass, call)
        try:
            success = await coordinator.nfc.register_tag(uid, name)
            return {"success": success, "uid": uid}
        except BoksError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=e.translation_key,
                translation_placeholders=e.translation_placeholders
            ) from e
        except Exception as e:
            _LOGGER.error("Error registering NFC tag: %s", e)
            raise HomeAssistantError(f"Unexpected error: {e}") from e

    hass.services.async_register(
        DOMAIN,
        "nfc_register_tag",
        handle_nfc_register_tag,
        schema=SERVICE_NFC_REGISTER_TAG_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL
    )

    # --- Service: Unregister NFC Tag ---
    async def handle_nfc_unregister_tag(call: ServiceCall):
        """Handle unregistering an NFC tag."""
        uid = call.data["uid"]
        coordinator = get_coordinator_from_call(hass, call)
        try:
            success = await coordinator.nfc.unregister_tag(uid)
            return {"success": success, "uid": uid}
        except BoksError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=e.translation_key,
                translation_placeholders=e.translation_placeholders
            ) from e
        except Exception as e:
            _LOGGER.error("Error unregistering NFC tag: %s", e)
            raise HomeAssistantError(f"Unexpected error: {e}") from e

    hass.services.async_register(
        DOMAIN,
        "nfc_unregister_tag",
        handle_nfc_unregister_tag,
        schema=SERVICE_NFC_UNREGISTER_TAG_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL
    )

    # --- Service: Ask Door Status ---
    async def handle_ask_door_status(call: ServiceCall) -> dict:
        """Handle the ask door status service call."""
        coordinator = get_coordinator_from_call(hass, call)
        return await coordinator.commands.ask_door_status()

    hass.services.async_register(
        DOMAIN,
        "ask_door_status",
        handle_ask_door_status,
        supports_response=SupportsResponse.OPTIONAL
    )

    # --- Service: Generate Update Package ---
    async def handle_generate_update_package(call: ServiceCall):
        """Handle generating the update package."""
        coordinator = get_coordinator_from_call(hass, call)
        target_version = call.data["version"]
        try:
            await coordinator.updates.generate_package(target_version)
        except Exception as e:
            _LOGGER.error("Failed to generate update package via service: %s", e)
            raise HomeAssistantError(f"Failed to generate update package: {e}") from e

    hass.services.async_register(
        DOMAIN,
        "generate_update_package",
        handle_generate_update_package,
        schema=SERVICE_GENERATE_UPDATE_PACKAGE_SCHEMA
    )

    # --- Service: Delete Update Package ---
    async def handle_delete_update_package(call: ServiceCall):
        """Handle deleting the update package."""
        coordinator = get_coordinator_from_call(hass, call)
        target_version = call.data["version"]
        try:
            await coordinator.updates.async_delete_package(target_version)
        except Exception as e:
            _LOGGER.error("Failed to delete update package via service: %s", e)
            raise HomeAssistantError(f"Failed to delete update package: {e}") from e

    hass.services.async_register(
        DOMAIN,
        "delete_update_package",
        handle_delete_update_package,
        schema=SERVICE_DELETE_UPDATE_PACKAGE_SCHEMA
    )

    # --- Service: Generate PIN Code ---
    async def handle_generate_pin_code(call: ServiceCall) -> dict:
        """Handle generating a PIN code."""
        coordinator = get_coordinator_from_call(hass, call)
        pin_type = call.data["type"]
        index = call.data["index"]

        try:
            pin = coordinator.pin_generator.generate_pin(pin_type, index)
            return {"pin": pin}
        except BoksError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=e.translation_key,
                translation_placeholders=e.translation_placeholders
            ) from e
        except Exception as e:
            _LOGGER.error("Error generating PIN code: %s", e)
            raise HomeAssistantError(f"Unexpected error: {e}") from e

    hass.services.async_register(
        DOMAIN,
        "generate_pin_code",
        handle_generate_pin_code,
        schema=SERVICE_GENERATE_PIN_CODE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL
    )
