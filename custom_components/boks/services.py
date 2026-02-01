"""Services for the Boks integration."""
import logging

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .ble.const import BoksConfigType
from .const import (
    DOMAIN,
    MAX_MASTER_CODE_CLEAN_RANGE,
)
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

SERVICE_ASK_DOOR_STATUS_SCHEMA = vol.Schema({}, extra=vol.ALLOW_EXTRA)


def get_coordinator_from_call(hass: HomeAssistant, call: ServiceCall) -> BoksDataUpdateCoordinator:
    """Retrieve the Boks coordinator from a service call target."""
    # 1. Try Device ID
    if "device_id" in call.data:
        coord = _get_coordinator_by_device_id(hass, call.data["device_id"])
        if coord:
            return coord

    # 2. Try Entity ID
    if "entity_id" in call.data:
        entity_id = call.data["entity_id"]
        if isinstance(entity_id, list):
            entity_id = entity_id[0]

        ent_reg = er.async_get(hass)
        entry = ent_reg.async_get(entity_id)
        if entry:
            dev_reg = dr.async_get(hass)
            device = dev_reg.async_get(entry.device_id)
            if device:
                coord = _get_coordinator_by_device_id(hass, device.id)
                if coord:
                    return coord

    # 3. Fallback: If only one Boks is configured, use it
    boks_coordinators = list(hass.data.get(DOMAIN, {}).values())
    if len(boks_coordinators) == 1:
        return boks_coordinators[0]

    if not boks_coordinators:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="no_devices_configured"
        )

    raise HomeAssistantError(
        translation_domain=DOMAIN,
        translation_key="multiple_devices_found"
    )

def _get_coordinator_by_device_id(hass: HomeAssistant, device_id: str) -> BoksDataUpdateCoordinator | None:
    """Find a Boks coordinator using its device ID."""
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get(device_id)
    if not device:
        return None

    # Check if this device belongs to our domain
    address = None
    for identifier in device.identifiers:
        if identifier[0] == DOMAIN:
            address = identifier[1]
            break

    if not address:
        return None

    # Find the corresponding config entry
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data.get("address") == address:
            return hass.data[DOMAIN].get(entry.entry_id)

    return None

async def async_setup_services(hass: HomeAssistant):
    """Set up services for the Boks integration."""

    # --- Service: Add Parcel ---
    async def handle_add_parcel(call: ServiceCall):
        """Handle adding a parcel."""
        description = call.data.get("description", "Colis")
        coordinator = get_coordinator_from_call(hass, call)

        # We look for the todo entity associated with this coordinator
        todo_list = None
        for entry in hass.config_entries.async_entries(DOMAIN):
            if entry.runtime_data == coordinator:
                ent_reg = er.async_get(hass)
                for entity in ent_reg.entities.values():
                    if entity.config_entry_id == entry.entry_id and entity.domain == "todo":
                        todo_list = entity
                        break

        if not todo_list:
             raise HomeAssistantError(
                 translation_domain=DOMAIN,
                 translation_key="todo_entity_not_found_for_device",
                 translation_placeholders={"target_device_id": coordinator.entry.entry_id}
             )

        await hass.services.async_call(
            "todo",
            "add_item",
            {
                "entity_id": todo_list.entity_id,
                "item": description
            },
            blocking=True
        )

    # --- Service: Open Door ---
    async def handle_open_door(call: ServiceCall):
        """Handle opening the door."""
        code = call.data.get("code")
        coordinator = get_coordinator_from_call(hass, call)

        try:
            await coordinator.ble_device.open_door(code)
        except BoksError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=e.translation_key,
                translation_placeholders=e.translation_placeholders
            ) from e
        except Exception as e:
            _LOGGER.error("Failed to open door: %s", e)
            raise HomeAssistantError(f"Failed to open door: {e}") from e

    # --- Service: Add Master Code ---
    async def handle_add_master_code(call: ServiceCall):
        """Handle adding a master code."""
        code = call.data["code"]
        index = call.data["index"]
        coordinator = get_coordinator_from_call(hass, call)

        try:
            await coordinator.ble_device.add_master_code(index, code)
            await coordinator.async_request_refresh()
        except BoksError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=e.translation_key,
                translation_placeholders=e.translation_placeholders
            ) from e

    # --- Service: Delete Master Code ---
    async def handle_delete_master_code(call: ServiceCall):
        """Handle deleting a master code."""
        index = call.data["index"]
        coordinator = get_coordinator_from_call(hass, call)

        try:
            await coordinator.ble_device.delete_master_code(index)
            await coordinator.async_request_refresh()
        except BoksError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=e.translation_key,
                translation_placeholders=e.translation_placeholders
            ) from e

    # --- Service: Add Single Use Code ---
    async def handle_add_single_code(call: ServiceCall):
        """Handle adding a single use code."""
        code = call.data["code"]
        coordinator = get_coordinator_from_call(hass, call)

        try:
            await coordinator.ble_device.add_single_use_code(code)
            await coordinator.async_request_refresh()
        except BoksError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=e.translation_key,
                translation_placeholders=e.translation_placeholders
            ) from e

    # --- Service: Delete Single Use Code ---
    async def handle_delete_single_code(call: ServiceCall):
        """Handle deleting a single use code."""
        code = call.data["code"]
        coordinator = get_coordinator_from_call(hass, call)

        try:
            await coordinator.ble_device.delete_single_use_code(code)
            await coordinator.async_request_refresh()
        except BoksError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=e.translation_key,
                translation_placeholders=e.translation_placeholders
            ) from e

    # --- Service: Add Multi Use Code ---
    async def handle_add_multi_code(call: ServiceCall):
        """Handle adding a multi use code."""
        code = call.data["code"]
        coordinator = get_coordinator_from_call(hass, call)

        try:
            await coordinator.ble_device.add_multi_use_code(code)
            await coordinator.async_request_refresh()
        except BoksError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=e.translation_key,
                translation_placeholders=e.translation_placeholders
            ) from e

    # --- Service: Delete Multi Use Code ---
    async def handle_delete_multi_code(call: ServiceCall):
        """Handle deleting a multi use code."""
        code = call.data["code"]
        coordinator = get_coordinator_from_call(hass, call)

        try:
            await coordinator.ble_device.delete_multi_use_code(code)
            await coordinator.async_request_refresh()
        except BoksError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=e.translation_key,
                translation_placeholders=e.translation_placeholders
            ) from e

    # --- Service: Sync Logs ---
    async def handle_sync_logs(call: ServiceCall):
        """Handle log synchronization."""
        coordinator = get_coordinator_from_call(hass, call)
        await coordinator.async_sync_logs()

    # --- Service: Clean Master Codes ---
    async def handle_clean_master_codes(call: ServiceCall):
        """Handle cleaning master codes."""
        start_index = call.data.get("start_index", 0)
        scan_range = call.data.get("range", MAX_MASTER_CODE_CLEAN_RANGE)
        coordinator = get_coordinator_from_call(hass, call)

        if coordinator.maintenance_status.get("running"):
             raise HomeAssistantError(
                 translation_domain=DOMAIN,
                 translation_key="maintenance_already_running"
             )

        hass.async_create_task(coordinator.ble_device.clean_master_codes(start_index, scan_range, coordinator))

    # --- Service: Set Configuration ---
    async def handle_set_configuration(call: ServiceCall):
        """Handle changing device configuration."""
        coordinator = get_coordinator_from_call(hass, call)

        if "laposte" in call.data:
            try:
                await coordinator.ble_device.set_configuration(BoksConfigType.SCAN_LAPOSTE_NFC_TAGS, call.data["laposte"])
                await coordinator.async_request_refresh()
            except BoksError as e:
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key=e.translation_key,
                    translation_placeholders=e.translation_placeholders
                ) from e

    # --- Service: Start NFC Scan ---
    async def handle_nfc_scan_start(call: ServiceCall):
        """Handle starting NFC scan mode."""
        coordinator = get_coordinator_from_call(hass, call)
        try:
            await coordinator.ble_device.start_nfc_scan()
        except BoksError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=e.translation_key,
                translation_placeholders=e.translation_placeholders
            ) from e

    # --- Service: Register NFC Tag ---
    async def handle_nfc_register_tag(call: ServiceCall):
        """Handle registering an NFC tag."""
        uid = call.data["uid"]
        name = call.data.get("name")
        coordinator = get_coordinator_from_call(hass, call)
        try:
            await coordinator.ble_device.register_nfc_tag(uid, name)
            await coordinator.async_request_refresh()
        except BoksError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=e.translation_key,
                translation_placeholders=e.translation_placeholders
            ) from e

    # --- Service: Unregister NFC Tag ---
    async def handle_nfc_unregister_tag(call: ServiceCall):
        """Handle unregistering an NFC tag."""
        uid = call.data["uid"]
        coordinator = get_coordinator_from_call(hass, call)
        try:
            await coordinator.ble_device.unregister_nfc_tag(uid)
            await coordinator.async_request_refresh()
        except BoksError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=e.translation_key,
                translation_placeholders=e.translation_placeholders
            ) from e

    # --- Service: Ask Door Status ---
    async def handle_ask_door_status(call: ServiceCall):
        """Handle manual door status request."""
        coordinator = get_coordinator_from_call(hass, call)
        try:
            await coordinator.ble_device.get_door_status()
            await coordinator.async_request_refresh()
        except BoksError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=e.translation_key,
                translation_placeholders=e.translation_placeholders
            ) from e


    # Register all services
    hass.services.async_register(DOMAIN, "add_parcel", handle_add_parcel, schema=SERVICE_ADD_PARCEL_SCHEMA)
    hass.services.async_register(DOMAIN, "open_door", handle_open_door, schema=SERVICE_OPEN_DOOR_SCHEMA)
    hass.services.async_register(DOMAIN, "add_master_code", handle_add_master_code, schema=SERVICE_ADD_MASTER_CODE_SCHEMA)
    hass.services.async_register(DOMAIN, "delete_master_code", handle_delete_master_code, schema=SERVICE_DELETE_MASTER_CODE_SCHEMA)
    hass.services.async_register(DOMAIN, "add_single_code", handle_add_single_code, schema=SERVICE_ADD_SINGLE_CODE_SCHEMA)
    hass.services.async_register(DOMAIN, "delete_single_code", handle_delete_single_code, schema=SERVICE_DELETE_SINGLE_CODE_SCHEMA)
    hass.services.async_register(DOMAIN, "add_multi_code", handle_add_multi_code, schema=SERVICE_ADD_MULTI_CODE_SCHEMA)
    hass.services.async_register(DOMAIN, "delete_multi_code", handle_delete_multi_code, schema=SERVICE_DELETE_MULTI_CODE_SCHEMA)
    hass.services.async_register(DOMAIN, "sync_logs", handle_sync_logs, schema=SERVICE_SYNC_LOGS_SCHEMA)
    hass.services.async_register(DOMAIN, "clean_master_codes", handle_clean_master_codes, schema=SERVICE_CLEAN_MASTER_CODES_SCHEMA)
    hass.services.async_register(DOMAIN, "set_configuration", handle_set_configuration, schema=SERVICE_SET_CONFIGURATION_SCHEMA)
    hass.services.async_register(DOMAIN, "nfc_scan_start", handle_nfc_scan_start, schema=SERVICE_NFC_SCAN_START_SCHEMA)
    hass.services.async_register(DOMAIN, "nfc_register_tag", handle_nfc_register_tag, schema=SERVICE_NFC_REGISTER_TAG_SCHEMA)
    hass.services.async_register(DOMAIN, "nfc_unregister_tag", handle_nfc_unregister_tag, schema=SERVICE_NFC_UNREGISTER_TAG_SCHEMA)
    hass.services.async_register(DOMAIN, "ask_door_status", handle_ask_door_status, schema=SERVICE_ASK_DOOR_STATUS_SCHEMA)
