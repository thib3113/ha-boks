import asyncio
import logging
import uuid
from datetime import timedelta

from homeassistant.util import dt as dt_util
from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_CONFIG_KEY, EVENT_PARCEL_COMPLETED, EVENT_LOGS_RETRIEVED
from .coordinator import BoksDataUpdateCoordinator
from .parcels.utils import parse_parcel_string, generate_random_code, format_parcel_item

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY_TEMPLATE = "boks_parcels_{}"

# Sync interval for pending codes
SYNC_INTERVAL = timedelta(minutes=1)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Boks todo list."""
    coordinator: BoksDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Initialize the store
    store = Store(
        hass,
        STORAGE_VERSION,
        STORAGE_KEY_TEMPLATE.format(entry.entry_id)
    )

    # Check if config key is present for BLE sync operations
    has_config_key = bool(entry.data.get(CONF_CONFIG_KEY))
    if not has_config_key:
        _LOGGER.info("Boks Config Key missing: Parcel Todo List will run in tracking-only mode (no code sync to Boks).")

    entity = BoksParcelTodoList(coordinator, entry, store, has_config_key)
    await entity.async_load_storage()
    async_add_entities([entity])


class BoksParcelTodoList(CoordinatorEntity, TodoListEntity):
    """A Boks Todo List to manage Parcels and Codes."""

    _attr_has_entity_name = True  # Use entity name directly without device prefix
    _attr_translation_key = "parcels"  # Use translation key for entity name
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
    )

    @property
    def translation_placeholders(self) -> dict[str, str]:
        """Return the translation placeholders."""
        return {}

    @property
    def suggested_object_id(self) -> str | None:
        """Return the suggested object id."""
        return "parcels"

    def __init__(
        self,
        coordinator: BoksDataUpdateCoordinator,
        entry: ConfigEntry,
        store: Store,
        has_config_key: bool # New parameter to indicate if config key is present
    ) -> None:
        """Initialize the Todo List."""
        super().__init__(coordinator)
        self._entry = entry
        self._store = store
        self._attr_unique_id = f"{entry.data[CONF_ADDRESS]}_parcels"
        self._items: list[TodoItem] = []
        self._raw_data = []
        self._has_config_key = has_config_key
        self._unsub_timer = None

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.data[CONF_ADDRESS])},
        )

    @property
    def todo_items(self) -> list[TodoItem] | None:
        """Return the items in the todo list."""
        # Return items with their original summaries, without any status information appended
        return [
            TodoItem(
                uid=item.uid,
                summary=item.summary,
                status=item.status
            )
            for item in self._items
        ]

    async def async_load_storage(self) -> None:
        """Load the items from storage."""
        data = await self._store.async_load()
        if data:
            self._items = [
                TodoItem(
                    uid=item["uid"],
                    summary=item["summary"],
                    status=TodoItemStatus(item["status"]),
                )
                for item in data
            ]
            # Store the raw data for metadata access
            self._raw_data = data
        else:
            self._raw_data = []

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()

        # Subscribe to log events to process them only when they are retrieved (once)
        self.async_on_remove(self.hass.bus.async_listen(EVENT_LOGS_RETRIEVED, self._handle_log_event))

        # Start periodic task to check for pending codes
        if self._has_config_key:
            self._unsub_timer = async_track_time_interval(
                self.hass, self._check_pending_codes, SYNC_INTERVAL
            )
            # Run once immediately to clear any backlog
            self.hass.async_create_task(self._check_pending_codes())

    async def async_will_remove_from_hass(self) -> None:
        """Handle entity removal."""
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None
        await super().async_will_remove_from_hass()

    @callback
    def _handle_log_event(self, event) -> None:
        """Handle new logs received from the device via event bus."""
        # Ensure we only process logs for this specific device
        if event.data.get("device_id") != self._entry.entry_id:
            return

        latest_logs = event.data.get("logs", [])
        _LOGGER.debug("Log event received, checking for parcel deliveries in %d logs.", len(latest_logs))

        if latest_logs:
            changed = False
            for log in latest_logs:
                # Check if this is a code usage event
                event_type = log.get("event_type", "")
                if event_type in ("code_ble_valid", "code_key_valid"):
                    used_code = log.get("code")
                    if used_code:
                        # Check all pending items for a matching code
                        for item in self._items:
                            if item.status == TodoItemStatus.NEEDS_ACTION:
                                item_code, description = parse_parcel_string(item.summary)
                                if item_code and item_code == used_code:
                                    _LOGGER.info("Parcel %s delivered! Marking as completed.", used_code)
                                    item.status = TodoItemStatus.COMPLETED
                                    # Update raw data
                                    for raw_item in self._raw_data:
                                        if raw_item["uid"] == item.uid:
                                            raw_item["status"] = item.status
                                            break
                                    changed = True

                                    _LOGGER.debug("Fire %s event : %s %s", EVENT_PARCEL_COMPLETED, item_code, description)
                                    self.hass.bus.async_fire(EVENT_PARCEL_COMPLETED, {
                                        "code": item_code,
                                        "description": description,
                                        "timestamp": dt_util.now().isoformat()
                                    })

            if changed:
                self.hass.async_create_task(self._async_save())
                _LOGGER.debug("Auto-completed todo items based on log event")
                self.async_write_ha_state()

    # NOTE: _handle_coordinator_update is removed/reverted to default because
    # we now handle logs via the event bus to avoid duplicate processing.
    # The default behavior (updating state) is sufficient for other data.
    async def _check_pending_codes(self, now=None) -> None:
        """Periodic task to sync pending codes to Boks."""
        pending_items = []
        for raw_item in self._raw_data:
            pending_code = raw_item.get("pending_sync_code")
            if pending_code:
                # Double check that the item exists in _items
                if any(x.uid == raw_item["uid"] for x in self._items):
                    pending_items.append(raw_item)

        if not pending_items:
            return

        _LOGGER.debug("Found %d items with pending codes to sync.", len(pending_items))

        # Process pending items
        # We process one by one to keep connection logic simple
        for raw_item in pending_items:
            uid = raw_item["uid"]
            code = raw_item["pending_sync_code"]
            retry_count = raw_item.get("sync_retry_count", 0)

            if retry_count >= 5:
                _LOGGER.warning("Aborting sync for code %s (Item %s) after %d failed attempts.", code, uid, retry_count)
                # Remove pending status to stop retry loop
                await self._update_todo_item_metadata_remove_pending(uid)
                continue

            try:
                _LOGGER.debug("Attempting to sync pending code %s for item %s (Attempt %d)", code, uid, retry_count + 1)
                await self.coordinator.ble_device.connect()

                # Check if we are still connected
                if not self.coordinator.ble_device.is_connected:
                     _LOGGER.warning("BLE connection failed, skipping sync for this run.")
                     break

                await self.coordinator.ble_device.create_pin_code(code, "single")
                _LOGGER.info("Successfully synced pending code %s to Boks.", code)

                # Update metadata to remove pending status
                await self._update_todo_item_metadata_remove_pending(uid)

            except Exception as e:
                _LOGGER.error("Failed to sync pending code %s: %s", code, e)
                # Increment retry count
                raw_item["sync_retry_count"] = retry_count + 1
                await self._async_save()
            finally:
                await asyncio.shield(self.coordinator.ble_device.disconnect())

    async def _update_todo_item_metadata_remove_pending(self, item_uid: str) -> None:
        """Remove the pending_sync_code from metadata."""
        try:
            for item in self._raw_data:
                if item["uid"] == item_uid:
                    item.pop("pending_sync_code", None)
                    item.pop("sync_retry_count", None)
                    # Legacy cleanup
                    item.pop("generation_status", None)
                    break

            await self._async_save()
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("Failed to update metadata after sync: %s", e)

    async def _async_save(self) -> None:
        """Save items to storage."""
        await self._store.async_save([
            {
                "uid": item.uid,
                "summary": item.summary,
                "status": item.status,
                # Preserve any existing metadata
                **self._get_item_metadata(item.uid)
            }
            for item in self._items
        ])

    def _get_item_metadata(self, uid: str) -> dict:
        """Get metadata for an item by UID."""
        for item in self._raw_data:
            if item["uid"] == uid:
                # Return a copy of all metadata fields (excluding the standard ones)
                metadata = item.copy()
                metadata.pop("uid", None)
                metadata.pop("summary", None)
                metadata.pop("status", None)
                return metadata
        return {}

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Add an item to the list."""
        await self.async_create_parcel(item.summary, force_background_sync=False)

    async def async_create_parcel(self, description: str, force_background_sync: bool = False) -> str | None:
        """
        Create a parcel item.

        Args:
            description: The text description (may include code).
            force_background_sync: If True, forces the item to be queued for background Boks sync
                                   even if a code is manually provided.

        Returns:
            The code associated with the parcel (if available/generated), or None if pending background generation.
        """
        _LOGGER.debug("Creating parcel. Description: %s, Force Sync: %s", description, force_background_sync)

        # 1. Parse input
        code, clean_desc = parse_parcel_string(description)

        final_code = code
        sync_required = False

        # 2. Handle Code / Generation Logic
        if final_code:
            if self._has_config_key and force_background_sync:
                 # Code provided, but sync requested (e.g. from service call)
                 _LOGGER.debug("Code '%s' provided with force_sync. Queuing background sync.", final_code)
                 sync_required = True
                 final_summary = format_parcel_item(final_code, clean_desc)

            elif self._has_config_key:
                # Code manually provided - Tracking only (Manual input = No BLE Sync)
                _LOGGER.debug("Code '%s' manually provided. Item tracking only (No BLE sync).", final_code)
                final_summary = format_parcel_item(final_code, clean_desc)

            else: # No key
                 final_summary = format_parcel_item(final_code, clean_desc)

        else: # No code provided
            if not self._has_config_key:
                # Degraded: No code generation
                final_code = None
                final_summary = format_parcel_item(final_code, clean_desc)
                _LOGGER.info("Degraded Mode: No Config Key. No code generated for tracking.")

            else: # Has key, need generation
                # Asynchronous Generation (UI Call)
                # Generate the code NOW, but sync it LATER
                final_code = generate_random_code()

                # Check uniqueness (best effort before sync)
                existing_codes = set()
                for item in self._items:
                    c, _ = parse_parcel_string(item.summary)
                    if c:
                        existing_codes.add(c)

                for _ in range(10):
                    if final_code not in existing_codes:
                        break
                    final_code = generate_random_code()

                final_summary = format_parcel_item(final_code, clean_desc)
                sync_required = True

        # 3. Create and Save Item
        new_uid = uuid.uuid4().hex
        new_item = TodoItem(
            uid=new_uid,
            summary=final_summary,
            status=TodoItemStatus.NEEDS_ACTION,
        )

        self._items.append(new_item)

        raw_item = {
            "uid": new_item.uid,
            "summary": final_summary,
            "status": new_item.status,
        }

        if sync_required:
            raw_item["pending_sync_code"] = final_code

        self._raw_data.append(raw_item)

        await self._async_save()
        self.async_write_ha_state()

        # We rely on the periodic task to pick this up.
        # But for UX responsiveness, we can trigger a check immediately (non-blocking)
        if sync_required:
             self.hass.async_create_task(self._check_pending_codes())

        return final_code

    async def _update_todo_item_metadata(self, item_uid: str, generation_status: str) -> None:
        """Update a todo item's metadata and save."""
        # Deprecated / Legacy support if needed
        pass

    async def _update_todo_item_description(self, item_uid: str, new_description: str) -> None:
        """Update a todo item's description and save."""
        await self._update_todo_item_description_and_metadata(item_uid, new_description, None)

    async def _update_todo_item_description_and_metadata(self, item_uid: str, new_description: str, generation_status: str | None) -> None:
        """Update a todo item's description and metadata and save."""
        try:
            # Find the item
            existing_index = next(i for i, x in enumerate(self._items) if x.uid == item_uid)
            existing_item = self._items[existing_index]

            # Update the summary
            existing_item.summary = new_description

            # Update metadata
            for item in self._raw_data:
                if item["uid"] == item_uid:
                    if generation_status is None:
                        # Remove generation status on success
                        item.pop("generation_status", None)
                    else:
                        item["generation_status"] = generation_status
                    break

            # Save and update state
            self._items[existing_index] = existing_item
            await self._async_save()
            self.async_write_ha_state()
        except StopIteration:
            _LOGGER.warning("Could not find todo item with UID %s to update description", item_uid)
        except Exception as e:
            _LOGGER.error("Failed to update todo item description and metadata: %s", e)

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update a todo item."""
        _LOGGER.debug("User requested update of todo item UID: %s, Changes: summary=%s, status=%s", item.uid, item.summary, item.status)
        # Find the existing item
        try:
            existing_index = next(i for i, x in enumerate(self._items) if x.uid == item.uid)
        except StopIteration:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="item_not_found"
            )

        existing_item = self._items[existing_index]

        # Case 1: Status Change (Completion)
        if item.status is not None:
            existing_item.status = item.status

        # Case 2: Summary Change (Renaming)
        if item.summary is not None and item.summary != existing_item.summary:
             old_code, _ = parse_parcel_string(existing_item.summary)
             new_code, new_desc = parse_parcel_string(item.summary)

             # If the code changed, we should check if there was a pending sync
             # If user manually changed code, abort pending sync for the old code
             if old_code != new_code:
                  for raw_item in self._raw_data:
                        if raw_item["uid"] == existing_item.uid:
                            if "pending_sync_code" in raw_item:
                                _LOGGER.info("Code changed manually from %s to %s. Removing pending sync for %s.", old_code, new_code, old_code)
                                raw_item.pop("pending_sync_code", None)
                            break

                  if new_code and self._has_config_key:
                       _LOGGER.debug("Code changed to '%s' in '%s'. Item tracking updated (No BLE sync for manual update).", new_code, item.summary)

             existing_item.summary = format_parcel_item(new_code, new_desc)

        # Update raw data to match the updated item
        for raw_item in self._raw_data:
            if raw_item["uid"] == existing_item.uid:
                raw_item["summary"] = existing_item.summary
                if item.status is not None:
                    raw_item["status"] = item.status
                break

        # Save
        self._items[existing_index] = existing_item
        _LOGGER.debug("Updated todo item with UID: %s, New Summary: %s, New Status: %s", existing_item.uid, existing_item.summary, existing_item.status)
        await self._async_save()
        self.async_write_ha_state()

    async def async_delete_todo_item(self, uid: str) -> None:
        """Delete a single todo item."""
        await self.async_delete_todo_items([uid])

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete todo items."""
        _LOGGER.debug("User requested deletion of todo items with UIDs: %s", uids)
        # Parse items to be deleted
        items_to_remove = []
        raw_items_to_remove = []

        for uid in uids:
            try:
                item = next(x for x in self._items if x.uid == uid)
                items_to_remove.append(item)
            except StopIteration:
                # Item not found, continue with others
                continue

        # Find corresponding raw data items to remove
        for item in items_to_remove:
            try:
                raw_item = next(x for x in self._raw_data if x["uid"] == item.uid)
                raw_items_to_remove.append(raw_item)
            except StopIteration:
                # Raw item not found, continue with others
                continue

        # Remove items from local list
        for item in items_to_remove:
            if item in self._items:  # Safety check
                self._items.remove(item)
                _LOGGER.debug("Deleted todo item with UID: %s", item.uid)

        # Remove items from raw data
        for raw_item in raw_items_to_remove:
            if raw_item in self._raw_data:  # Safety check
                self._raw_data.remove(raw_item)
                _LOGGER.debug("Deleted raw data for todo item with UID: %s", raw_item["uid"])

        await self._async_save()
        self.async_write_ha_state()
