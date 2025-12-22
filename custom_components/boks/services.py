"Services for the Boks integration."
import logging
import voluptuous as vol
import asyncio

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, CONF_CONFIG_KEY, MAX_MASTER_CODE_CLEAN_RANGE
from .coordinator import BoksDataUpdateCoordinator
from .errors import BoksError
from .todo import BoksParcelTodoList
from .parcels.utils import parse_parcel_string, generate_random_code, format_parcel_item

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

SERVICE_ENABLE_LAPOSTE_SCHEMA = vol.Schema({
    vol.Required("enable"): cv.boolean,
}, extra=vol.ALLOW_EXTRA)


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
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="target_devices_not_boks",
            translation_placeholders={"device_ids": str(device_ids)}
        )

    # 2. Try Entity ID
    entity_ids = call.data.get("entity_id")
    if entity_ids:
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]

        # Retrieve registry to map entity -> config_entry
        registry = er.async_get(hass)

        for entity_id in entity_ids:
            entry = registry.async_get(entity_id)
            if entry and entry.config_entry_id in hass.data[DOMAIN]:
                return hass.data[DOMAIN][entry.config_entry_id]

        # If entity_ids were provided but we didn't return above, none were Boks entities
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="target_entities_not_boks",
            translation_placeholders={"entity_ids": str(entity_ids)}
        )

    # 3. Fallback: Single Instance (Only if NO target was provided)
    if len(hass.data[DOMAIN]) == 1:
        # Only check actual coordinator instances (skip 'translations' key if present)
        coords = [v for k, v in hass.data[DOMAIN].items() if isinstance(v, BoksDataUpdateCoordinator)]
        if len(coords) == 1:
            return coords[0]

    # 4. Fail
    raise HomeAssistantError(
        translation_domain=DOMAIN,
        translation_key="target_device_missing"
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

        # Get the lock entity to use its open logic (which handles fallback/generation)
        # We need to find the lock entity associated with this coordinator
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
            # Use entity logic
            await lock_entity.async_open(code=code)
        else:
            # Fallback to direct BLE open (less robust, no state update logic in coordinator)
            # But async_open is on the entity...
            # We should probably error if no lock entity found
            raise HomeAssistantError("lock_entity_not_found")

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
        code_in_desc, parsed_description = parse_parcel_string(description)
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
        _LOGGER.info(f"Adding PIN Code: Code={masked_code}, Type={code_type}, Index={index}")

        coordinator = get_coordinator_from_call(hass, call)
        await coordinator.ble_device.connect()
        try:
            created_code = await coordinator.ble_device.create_pin_code(code, code_type, index)
            _LOGGER.info(f"Code {created_code} ({code_type}) added successfully.")
            await coordinator.async_request_refresh()
            return {"code": created_code}
        except BoksError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=e.translation_key,
                translation_placeholders=e.translation_placeholders
            ) from e
        finally:
            await asyncio.shield(coordinator.ble_device.disconnect())

    async def _handle_delete_code(call: ServiceCall, code_type: str, identifier: str | int):
        if isinstance(identifier, str):
            identifier = identifier.strip().upper()

        _LOGGER.info(f"Deleting PIN Code: Identifier={identifier}, Type={code_type}")

        coordinator = get_coordinator_from_call(hass, call)
        await coordinator.ble_device.connect()
        try:
            success = await coordinator.ble_device.delete_pin_code(code_type, identifier)
            if not success:
                 raise BoksError("delete_code_failed")

            _LOGGER.info(f"Code {identifier} ({code_type}) deleted successfully.")
            await coordinator.async_request_refresh()
        except BoksError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=e.translation_key,
                translation_placeholders=e.translation_placeholders
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

    # --- Service: Clean Master Codes ---
    async def handle_clean_master_codes(call: ServiceCall):
        """Handle the clean master codes service call."""
        start_index = call.data.get("start_index", 0)
        range_val = call.data.get("range", MAX_MASTER_CODE_CLEAN_RANGE)
        if range_val > MAX_MASTER_CODE_CLEAN_RANGE:
            _LOGGER.warning(f"Requested range {range_val} exceeds limit. Capping at {MAX_MASTER_CODE_CLEAN_RANGE}.")
            range_val = MAX_MASTER_CODE_CLEAN_RANGE

        coordinator = get_coordinator_from_call(hass, call)

        current_status = getattr(coordinator, "maintenance_status", {})
        if current_status.get("running", False):
            _LOGGER.warning("Clean Master Codes requested but a maintenance task is already running.")
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="maintenance_already_running"
            )

        _LOGGER.info(f"Clean Master Codes requested: Start={start_index}, Range={range_val}")

        async def _background_clean():
            total_to_clean = range_val
            current_idx = start_index
            coordinator.set_maintenance_status(
                running=True,
                current_index=current_idx,
                total_to_clean=total_to_clean,
                message="Starting..."
            )
            cleaned_count = 0

            try:
                if not coordinator.ble_device.is_connected:
                    await coordinator.ble_device.connect()

                for i in range(range_val):
                    target_index = start_index + i
                    current_progress_msg = f"Cleaning index {target_index}..."
                    coordinator.set_maintenance_status(
                        running=True,
                        current_index=i + 1,
                        total_to_clean=total_to_clean,
                        message=current_progress_msg
                    )

                    retry_count = 0
                    max_retries = 3
                    success = False

                    while retry_count < max_retries and not success:
                        try:
                            if not coordinator.ble_device.is_connected:
                                _LOGGER.debug(f"Reconnecting for index {target_index}...")
                                await coordinator.ble_device.connect()

                            await coordinator.ble_device.delete_pin_code(type="master", index_or_code=target_index)
                            cleaned_count += 1
                            await asyncio.sleep(0.2)
                            success = True

                        except Exception as e:
                            retry_count += 1
                            _LOGGER.warning(f"Error cleaning index {target_index} (Attempt {retry_count}/{max_retries}): {e}")
                            await asyncio.sleep(1.0)

                    if not success:
                        _LOGGER.error(f"Failed to clean index {target_index} after {max_retries} attempts. Aborting.")
                        raise Exception("Connection lost or device unresponsive")

                coordinator.set_maintenance_status(
                    running=False,
                    current_index=total_to_clean,
                    total_to_clean=total_to_clean,
                    message="Finished"
                )
                await hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "message": f"Master Code Cleaning Completed.\nScanned {range_val} indices starting from {start_index}.",
                        "title": "Boks Maintenance",
                        "notification_id": f"boks_maintenance_{coordinator.entry.entry_id}"
                    }
                )

            except Exception as e:
                _LOGGER.error(f"Maintenance task failed: {e}")
                coordinator.set_maintenance_status(running=False, message=f"Failed: {e}")
                await hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "message": f"Master Code Cleaning Failed at index {current_idx}.\nError: {e}",
                        "title": "Boks Maintenance Error",
                        "notification_id": f"boks_maintenance_{coordinator.entry.entry_id}"
                    }
                )

            finally:
                 await asyncio.shield(coordinator.ble_device.disconnect())
                 await asyncio.sleep(60)
                 coordinator.set_maintenance_status(running=False, message="")

        hass.async_create_task(_background_clean())

    hass.services.async_register(
        DOMAIN,
        "clean_master_codes",
        handle_clean_master_codes,
        schema=SERVICE_CLEAN_MASTER_CODES_SCHEMA
    )

    # --- Service: Enable La Poste ---
    async def handle_enable_laposte(call: ServiceCall):
        """Handle the enable La Poste service call."""
        enable = call.data["enable"]
        coordinator = get_coordinator_from_call(hass, call)

        await coordinator.ble_device.connect()
        try:
            await coordinator.ble_device.enable_laposte(enable)
            _LOGGER.info(f"La Poste configuration set to {enable}")
        except BoksError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=e.translation_key,
                translation_placeholders=e.translation_placeholders
            ) from e
        finally:
            await asyncio.shield(coordinator.ble_device.disconnect())

    # hass.services.async_register(
    #     DOMAIN,
    #     "enable_laposte",
    #     handle_enable_laposte,
    #     schema=SERVICE_ENABLE_LAPOSTE_SCHEMA
    # )
