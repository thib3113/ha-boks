"Services for the Boks integration."
import asyncio
import logging

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .ble.const import BoksConfigType
from .const import DOMAIN, MAX_MASTER_CODE_CLEAN_RANGE, TIMEOUT_NFC_LISTENING, TIMEOUT_NFC_WAIT_RESULT
from .coordinator import BoksDataUpdateCoordinator
from .errors import BoksError
from .logic.anonymizer import BoksAnonymizer
from .parcels.utils import format_parcel_item, generate_random_code, parse_parcel_string
from .todo import BoksParcelTodoList

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
                    return BoksDataUpdateCoordinator(hass, config_entry)

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
                return BoksDataUpdateCoordinator(hass, config_entry)

    raise HomeAssistantError(
        translation_domain=DOMAIN,
        translation_key="target_entities_not_boks",
        translation_placeholders={"entity_ids": str(entity_ids)}
    )


async def async_setup_services(hass: HomeAssistant):
    """Register services for the Boks integration."""

    # --- Service: Open Door ---
    async def handle_open_door(call: ServiceCall):
        """Handle the open door service call."""
        code = call.data.get("code")
        if code:
            code = code.strip().upper()

        coordinator = get_coordinator_from_call(hass, call)
        _LOGGER.info("Open Door requested via service for %s",
                     BoksAnonymizer.anonymize_mac(coordinator.ble_device.address, coordinator.ble_device.anonymize_logs))

        # Get the lock entity to use its open logic
        lock_entity = None
        entity_registry = er.async_get(hass)
        entries = er.async_entries_for_config_entry(entity_registry, coordinator.entry.entry_id)
        for entry in entries:
            if entry.domain == "lock":
                component = hass.data.get("entity_components", {}).get("lock")
                if component:
                    lock_entity = component.get_entity(entry.entity_id)
                    break

        if lock_entity:
            await lock_entity.async_open(code=code)
            _LOGGER.info("Open Door service completed for %s",
                         BoksAnonymizer.anonymize_mac(coordinator.ble_device.address, coordinator.ble_device.anonymize_logs))
        else:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="lock_entity_not_found"
            )

    hass.services.async_register(
        DOMAIN,
        "open_door",
        handle_open_door,
        schema=SERVICE_OPEN_DOOR_SCHEMA
    )

    # --- Service: Add Parcel ---
    async def handle_add_parcel(call: ServiceCall) -> dict | None:
        """Handle the add parcel service call."""
        description = call.data.get("description", "")
        _LOGGER.info("Add Parcel requested: %s", description)
        target_entity_id = None

        # 1. Try to get entity_id directly
        if "entity_id" in call.data:
            entity_ids = call.data["entity_id"]
            if isinstance(entity_ids, list) and len(entity_ids) > 0:
                 target_entity_id = entity_ids[0]
            elif isinstance(entity_ids, str):
                 target_entity_id = entity_ids

        # 2. If no entity_id, try to resolve from device_id
        if not target_entity_id and "device_id" in call.data:
            device_ids = call.data["device_id"]
            if isinstance(device_ids, str):
                device_ids = [device_ids]

            if device_ids:
                target_device_id = device_ids[0]
                entity_registry = er.async_get(hass)
                entries = entity_registry.entities.values()
                for entry in entries:
                    if entry.device_id == target_device_id and entry.domain == "todo":
                        target_entity_id = entry.entity_id
                        break

                if not target_entity_id:
                     raise HomeAssistantError(
                         translation_domain=DOMAIN,
                         translation_key="todo_entity_not_found_for_device",
                         translation_placeholders={"target_device_id": target_device_id}
                     )

        # 3. Fallback (Single Instance)
        if not target_entity_id:
            boks_entry_ids = list(hass.data[DOMAIN].keys())
            # Filter valid entries
            boks_entry_ids = [k for k in boks_entry_ids if k != "translations"]

            if len(boks_entry_ids) == 1:
                config_entry_id = boks_entry_ids[0]
                entity_registry = er.async_get(hass)
                entries = entity_registry.entities.values()
                for entry in entries:
                    if entry.config_entry_id == config_entry_id and entry.domain == "todo":
                        target_entity_id = entry.entity_id
                        break
            elif len(boks_entry_ids) > 1:
                 raise HomeAssistantError(
                     translation_domain=DOMAIN,
                     translation_key="multiple_devices_found"
                 )
            else:
                 raise HomeAssistantError(
                     translation_domain=DOMAIN,
                     translation_key="no_devices_configured"
                 )

        if not target_entity_id:
             raise HomeAssistantError(
                 translation_domain=DOMAIN,
                 translation_key="cannot_resolve_todo"
             )

        # 3. Get Actual Entity Object
        component = hass.data.get("entity_components", {}).get("todo")
        if not component:
             raise HomeAssistantError(
                 translation_domain=DOMAIN,
                 translation_key="todo_integration_not_loaded"
             )

        todo_entity = component.get_entity(target_entity_id)

        if not todo_entity:
             raise HomeAssistantError(
                 translation_domain=DOMAIN,
                 translation_key="todo_entity_not_found",
                 translation_placeholders={"target_entity_id": target_entity_id}
             )

        # 4. Verify it's a Boks entity
        if not isinstance(todo_entity, BoksParcelTodoList):
             raise HomeAssistantError(
                 translation_domain=DOMAIN,
                 translation_key="entity_not_parcel_list",
                 translation_placeholders={"target_entity_id": target_entity_id}
             )

        # 5. Generate/Parse Code and Create Parcel
        has_config_key = getattr(todo_entity, "_has_config_key", False)
        code_in_desc, _ = parse_parcel_string(description)
        generated_code = None
        force_sync = False

        if not code_in_desc:
            generated_code = generate_random_code()
            if has_config_key:
                force_sync = True
            formatted_description = format_parcel_item(generated_code, description or "Parcel")
        else:
            formatted_description = description
            generated_code = code_in_desc
            force_sync = False

        await todo_entity.async_create_parcel(formatted_description, force_background_sync=force_sync)
        _LOGGER.info("Add Parcel completed. Code: %s", generated_code)

        return {"code": generated_code}

    hass.services.async_register(
        DOMAIN,
        "add_parcel",
        handle_add_parcel,
        schema=SERVICE_ADD_PARCEL_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL
    )

    # --- Common Helpers for Code Operations ---
    async def _handle_create_code(call: ServiceCall, code: str, code_type: str, index: int = 0) -> dict:
        code = code.strip().upper()
        masked_code = "***" + code[-2:] if len(code) > 2 else "***"
        _LOGGER.info("Adding PIN Code: Code=%s, Type=%s, Index=%d", masked_code, code_type, index)

        try:
            coordinator = get_coordinator_from_call(hass, call)
            await coordinator.ble_device.connect()
            created_code = await coordinator.ble_device.create_pin_code(code, code_type, index)
            _LOGGER.info("Code %s (%s) added successfully.", created_code, code_type)
            await coordinator.async_request_refresh()
            return {"code": created_code}
        except BoksError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=e.translation_key,
                translation_placeholders=e.translation_placeholders
            ) from e
        except Exception as e:
            _LOGGER.error("Error creating code: %s", e)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="unexpected_create_code_error",
                translation_placeholders={"error": str(e)}
            ) from e
        finally:
            await asyncio.shield(coordinator.ble_device.disconnect())

    async def _handle_delete_code(call: ServiceCall, code_type: str, identifier: str | int):
        if isinstance(identifier, str):
            identifier = identifier.strip().upper()

        _LOGGER.info("Deleting PIN Code: Identifier=%s, Type=%s", identifier, code_type)

        try:
            coordinator = get_coordinator_from_call(hass, call)
            await coordinator.ble_device.connect()
            success = await coordinator.ble_device.delete_pin_code(code_type, identifier)
            if not success:
                 raise BoksError("delete_code_failed")

            _LOGGER.info("Code %s (%s) deleted successfully.", identifier, code_type)
            await coordinator.async_request_refresh()
        except BoksError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=e.translation_key,
                translation_placeholders=e.translation_placeholders
            ) from e
        except Exception as e:
            _LOGGER.error("Error deleting code: %s", e)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="unexpected_delete_code_error",
                translation_placeholders={"error": str(e)}
            ) from e
        finally:
            await asyncio.shield(coordinator.ble_device.disconnect())

    # --- Service: Add Master Code ---
    async def handle_add_master_code(call: ServiceCall) -> dict:
        return await _handle_create_code(call, call.data["code"], "master", call.data["index"])

    hass.services.async_register(
        DOMAIN,
        "add_master_code",
        handle_add_master_code,
        schema=SERVICE_ADD_MASTER_CODE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL
    )

    # --- Service: Delete Master Code ---
    async def handle_delete_master_code(call: ServiceCall):
        await _handle_delete_code(call, "master", call.data["index"])

    hass.services.async_register(
        DOMAIN,
        "delete_master_code",
        handle_delete_master_code,
        schema=SERVICE_DELETE_MASTER_CODE_SCHEMA
    )

    # --- Service: Add Single Code ---
    async def handle_add_single_code(call: ServiceCall) -> dict:
        return await _handle_create_code(call, call.data["code"], "single")

    hass.services.async_register(
        DOMAIN,
        "add_single_code",
        handle_add_single_code,
        schema=SERVICE_ADD_SINGLE_CODE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL
    )

    # --- Service: Delete Single Code ---
    async def handle_delete_single_code(call: ServiceCall):
        await _handle_delete_code(call, "single", call.data["code"])

    hass.services.async_register(
        DOMAIN,
        "delete_single_code",
        handle_delete_single_code,
        schema=SERVICE_DELETE_SINGLE_CODE_SCHEMA
    )

    # --- Service: Add Multi Code ---
    async def handle_add_multi_code(call: ServiceCall) -> dict:
        return await _handle_create_code(call, call.data["code"], "multi")

    hass.services.async_register(
        DOMAIN,
        "add_multi_code",
        handle_add_multi_code,
        schema=SERVICE_ADD_MULTI_CODE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL
    )

    # --- Service: Delete Multi Code ---
    async def handle_delete_multi_code(call: ServiceCall):
        await _handle_delete_code(call, "multi", call.data["code"])

    hass.services.async_register(
        DOMAIN,
        "delete_multi_code",
        handle_delete_multi_code,
        schema=SERVICE_DELETE_MULTI_CODE_SCHEMA
    )

    # --- Service: Sync Logs ---
    async def handle_sync_logs(call: ServiceCall):
        """Handle the sync logs service call."""
        coordinator = get_coordinator_from_call(hass, call)
        _LOGGER.info("Manual log sync requested via service for %s",
                     BoksAnonymizer.anonymize_mac(coordinator.ble_device.address, coordinator.ble_device.anonymize_logs))
        try:
            await coordinator.async_sync_logs(update_state=True)
            _LOGGER.info("Manual log sync completed for %s",
                         BoksAnonymizer.anonymize_mac(coordinator.ble_device.address, coordinator.ble_device.anonymize_logs))
        except Exception as e:
            _LOGGER.error("Failed to sync logs via service: %s", e)
            raise

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
        if range_val > MAX_MASTER_CODE_CLEAN_RANGE:
            _LOGGER.warning("Requested range %d exceeds limit. Capping at %d.", range_val, MAX_MASTER_CODE_CLEAN_RANGE)
            range_val = MAX_MASTER_CODE_CLEAN_RANGE

        coordinator = get_coordinator_from_call(hass, call)

        current_status = getattr(coordinator, "maintenance_status", {})
        if current_status.get("running", False):
            _LOGGER.warning("Clean Master Codes requested but a maintenance task is already running.")
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="maintenance_already_running"
            )

        _LOGGER.info("Clean Master Codes requested: Start=%d, Range=%d", start_index, range_val)

        async def _background_clean():
            total_to_clean = range_val
            current_idx = start_index
            coordinator.set_maintenance_status(
                running=True,
                current_index=current_idx,
                total_to_clean=total_to_clean
            )

            cleaned_count = 0

            try:
                if not coordinator.ble_device.is_connected:
                    await coordinator.ble_device.connect()

                for i in range(range_val):
                    target_index = start_index + i
                    coordinator.set_maintenance_status(
                        running=True,
                        current_index=i + 1,
                        total_to_clean=total_to_clean,
                        cleaned_count=cleaned_count
                    )

                    retry_count = 0
                    max_retries = 3
                    success = False

                    while retry_count < max_retries and not success:
                        try:
                            if not coordinator.ble_device.is_connected:
                                _LOGGER.debug("Reconnecting for index %d...", target_index)
                                await coordinator.ble_device.connect()

                            await coordinator.ble_device.delete_pin_code(type="master", index_or_code=target_index)
                            cleaned_count += 1
                            await asyncio.sleep(0.2)
                            success = True

                        except Exception as e:
                            retry_count += 1
                            _LOGGER.warning("Error cleaning index %d (Attempt %d/%d): %s", target_index, retry_count, max_retries, e)
                            await asyncio.sleep(1.0)

                    if not success:
                        _LOGGER.error("Failed to clean index %d after %d attempts. Aborting.", target_index, max_retries)
                        raise BoksError("connection_failed")

                coordinator.set_maintenance_status(
                    running=False,
                    current_index=total_to_clean,
                    total_to_clean=total_to_clean,
                    cleaned_count=cleaned_count
                )

                await hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "message": coordinator.get_text("common", "maintenance_success_msg", range=range_val, start_index=start_index),
                        "title": coordinator.get_text("common", "maintenance_success_title"),
                        "notification_id": f"boks_maintenance_{coordinator.entry.entry_id}"
                    }
                )

            except Exception as e:
                _LOGGER.error("Maintenance task failed: %s", e)
                coordinator.set_maintenance_status(running=False, error=str(e))

                await hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "message": coordinator.get_text("exceptions", "maintenance_error_msg", current_idx=current_idx, error=str(e)),
                        "title": coordinator.get_text("exceptions", "maintenance_error_title"),
                        "notification_id": f"boks_maintenance_{coordinator.entry.entry_id}"
                    }
                )

            finally:
                 await asyncio.shield(coordinator.ble_device.disconnect())
                 await asyncio.sleep(60)
                 coordinator.set_maintenance_status(running=False)

        hass.async_create_task(_background_clean())

    hass.services.async_register(
        DOMAIN,
        "clean_master_codes",
        handle_clean_master_codes,
        schema=SERVICE_CLEAN_MASTER_CODES_SCHEMA
    )

    # --- Service: Set Configuration ---
    async def handle_set_configuration(call: ServiceCall):
        """Handle the set configuration service call."""
        try:
            coordinator = get_coordinator_from_call(hass, call)

            # Check each supported configuration option
            # Initially only laposte
            laposte = call.data.get("laposte")

            if laposte is not None:
                # Check software revision if trying to enable laposte
                if laposte:
                    await coordinator.updates.ensure_prerequisites("La Poste", "4.0", "4.2.0")

                _LOGGER.info("Setting La Poste configuration to %s", laposte)
                await coordinator.ble_device.connect()
                try:
                    await coordinator.ble_device.set_configuration(BoksConfigType.SCAN_LAPOSTE_NFC_TAGS, laposte)
                finally:
                    await asyncio.shield(coordinator.ble_device.disconnect())
        except BoksError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=e.translation_key,
                translation_placeholders=e.translation_placeholders
            ) from e
        except Exception as e:
            _LOGGER.error("Error setting configuration: %s", e)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="unexpected_set_configuration_error",
                translation_placeholders={"error": str(e)}
            ) from e

    hass.services.async_register(
        DOMAIN,
        "set_configuration",
        handle_set_configuration,
        schema=SERVICE_SET_CONFIGURATION_SCHEMA
    )

    # --- Service: NFC Scan Start ---
    async def handle_nfc_scan_start(call: ServiceCall):
        """Handle NFC Scan Start."""
        coordinator = get_coordinator_from_call(hass, call)
        # Verify prerequisites synchronously
        await coordinator.updates.ensure_prerequisites("NFC", "4.0", "4.3.3")

        async def _run_scan():
            try:
                _LOGGER.info("Starting NFC scan session...")
                await coordinator.ble_device.connect()

                # Notify user that scan is active
                await hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "message": coordinator.get_text("common", "nfc_scan_started_msg"),
                        "title": coordinator.get_text("common", "nfc_scan_started_title"),
                        "notification_id": f"boks_nfc_scan_{coordinator.entry.entry_id}"
                    }
                )

                # This launches the scan on device.
                success = await coordinator.ble_device.nfc_scan_start()

                if success:
                    # We wait for the device to report a result
                    _LOGGER.info("NFC scan started, waiting for tag (%ds)...", int(TIMEOUT_NFC_LISTENING))

                    scan_done = asyncio.Event()
                    def scan_callback(data):
                        # 0xC5 (Found), 0xC6 (Already exists), 0xC7 (Timeout)
                        if data[0] in (0xC5, 0xC6, 0xC7):
                            _LOGGER.debug("NFC Scan result received: 0x%02X", data[0])
                            scan_done.set()

                    coordinator.ble_device.register_opcode_callback(0xC5, scan_callback)
                    coordinator.ble_device.register_opcode_callback(0xC6, scan_callback)
                    coordinator.ble_device.register_opcode_callback(0xC7, scan_callback)

                    try:
                        await asyncio.wait_for(scan_done.wait(), timeout=TIMEOUT_NFC_WAIT_RESULT)
                    except TimeoutError:
                        _LOGGER.warning("NFC scan session timed out (no response from device).")
                    finally:
                        coordinator.ble_device.unregister_opcode_callback(0xC5, scan_callback)
                        coordinator.ble_device.unregister_opcode_callback(0xC6, scan_callback)
                        coordinator.ble_device.unregister_opcode_callback(0xC7, scan_callback)
                else:
                    _LOGGER.error("Failed to start NFC scan on device")

            except Exception as e:
                _LOGGER.error("Error in NFC scan background task: %s", e)
            finally:
                # Decouple disconnect to ensure it runs
                await asyncio.shield(coordinator.ble_device.disconnect())

        # Launch as background task immediately
        hass.async_create_task(_run_scan())

    hass.services.async_register(
        DOMAIN,
        "nfc_scan_start",
        handle_nfc_scan_start,
        schema=SERVICE_NFC_SCAN_START_SCHEMA
    )

    # --- Service: NFC Register Tag ---
    async def handle_nfc_register_tag(call: ServiceCall):
        """Handle NFC Register Tag."""
        uid = call.data["uid"]
        name = call.data.get("name")

        coordinator = get_coordinator_from_call(hass, call)
        await coordinator.updates.ensure_prerequisites("NFC", "4.0", "4.3.3")

        try:

            await coordinator.ble_device.connect()
            success = await coordinator.ble_device.nfc_register_tag(uid)

            if success:
                # Optionally add to HA Tag Registry if name provided
                if name:
                    try:
                        tag_manager = hass.data.get("tag")
                        tags_helper = tag_manager.get("tags") if isinstance(tag_manager, dict) else tag_manager

                        if tags_helper:
                            tag_id = uid.replace(":", "").upper()
                            # Check if already exists to avoid error, skip update as requested
                            if hasattr(tags_helper, "data") and tag_id in tags_helper.data:
                                _LOGGER.info("Tag %s already exists in registry, skipping HA creation.", tag_id)
                            elif hasattr(tags_helper, "async_create_item"):
                                await tags_helper.async_create_item({"tag_id": tag_id, "name": name})
                                _LOGGER.info("Created HA Tag: %s (%s)", name, tag_id)
                        else:
                            _LOGGER.warning("Home Assistant 'tag' integration is not loaded or does not support item creation")
                    except Exception as e:
                        _LOGGER.error("Could not create/update HA Tag: %s", e)
        except BoksError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=e.translation_key,
                translation_placeholders=e.translation_placeholders
            ) from e
        except Exception as e:
            _LOGGER.error("Error registering NFC tag: %s", e)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="unexpected_register_tag_error",
                translation_placeholders={"error": str(e)}
            ) from e
        finally:
             await asyncio.shield(coordinator.ble_device.disconnect())

    hass.services.async_register(
        DOMAIN,
        "nfc_register_tag",
        handle_nfc_register_tag,
        schema=SERVICE_NFC_REGISTER_TAG_SCHEMA
    )

    # --- Service: NFC Unregister Tag ---
    async def handle_nfc_unregister_tag(call: ServiceCall):
        """Handle NFC Unregister Tag."""
        uid = call.data["uid"]
        try:
            coordinator = get_coordinator_from_call(hass, call)
            await coordinator.updates.ensure_prerequisites("NFC", "4.0", "4.3.3")

            await coordinator.ble_device.connect()
            await coordinator.ble_device.nfc_unregister_tag(uid)
        except BoksError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=e.translation_key,
                translation_placeholders=e.translation_placeholders
            ) from e
        except Exception as e:
            _LOGGER.error("Error unregistering NFC tag: %s", e)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="unexpected_unregister_tag_error",
                translation_placeholders={"error": str(e)}
            ) from e
        finally:
             await asyncio.shield(coordinator.ble_device.disconnect())

    hass.services.async_register(
        DOMAIN,
        "nfc_unregister_tag",
        handle_nfc_unregister_tag,
        schema=SERVICE_NFC_UNREGISTER_TAG_SCHEMA
    )

    # --- Service: Ask Door Status ---
    async def handle_ask_door_status(call: ServiceCall) -> dict:
        """Handle the ask door status service call."""
        coordinator = get_coordinator_from_call(hass, call)
        _LOGGER.info("Door status poll requested via service for %s",
                     BoksAnonymizer.anonymize_mac(coordinator.ble_device.address, coordinator.ble_device.anonymize_logs))

        try:
            await coordinator.ble_device.connect()
            is_open = await coordinator.ble_device.get_door_status()

            _LOGGER.info("Door status poll completed. Open: %s", is_open)
            return {"is_open": is_open}
        finally:
            await asyncio.shield(coordinator.ble_device.disconnect())

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
