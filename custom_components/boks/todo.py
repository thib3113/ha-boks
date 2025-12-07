from datetime import timedelta
from homeassistant.helpers.event import async_track_time_interval
import logging
import uuid

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.storage import Store
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import CONF_ADDRESS

from .const import DOMAIN, EVENT_LOG, CONF_CONFIG_KEY, EVENT_PARCEL_COMPLETED
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
        return {"name": self._entry.title}

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

    async def _check_pending_codes(self, now=None) -> None:
        """Periodic task to sync pending codes to Boks."""
        pending_items = []
        for raw_item in self._raw_data:
            pending_code = raw_item.get("pending_sync_code")
            if pending_code:
                # Double check that the item exists in _items
                if any(x.uid == raw_item["uid"] for x in self._items):
                    pending_items.append((raw_item["uid"], pending_code))
        
        if not pending_items:
            return

        _LOGGER.debug(f"Found {len(pending_items)} items with pending codes to sync.")
        
        # Process pending items
        # We process one by one to keep connection logic simple
        for uid, code in pending_items:
            try:
                _LOGGER.debug(f"Attempting to sync pending code {code} for item {uid}")
                await self.coordinator.ble_device.connect()
                
                # Check if we are still connected
                if not self.coordinator.ble_device.is_connected:
                     _LOGGER.warning("BLE connection failed, skipping sync for this run.")
                     break 

                await self.coordinator.ble_device.create_pin_code(code, "single")
                _LOGGER.info(f"Successfully synced pending code {code} to Boks.")
                
                # Update metadata to remove pending status
                await self._update_todo_item_metadata_remove_pending(uid)
                
            except Exception as e:
                _LOGGER.error(f"Failed to sync pending code {code}: {e}")
                # We leave it pending, will retry next interval
            finally:
                await self.coordinator.ble_device.disconnect()

    async def _update_todo_item_metadata_remove_pending(self, item_uid: str) -> None:
        """Remove the pending_sync_code from metadata."""
        try:
            for item in self._raw_data:
                if item["uid"] == item_uid:
                    item.pop("pending_sync_code", None)
                    # Legacy cleanup
                    item.pop("generation_status", None)
                    break
            
            await self._async_save()
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error(f"Failed to update metadata after sync: {e}")

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
                 _LOGGER.debug(f"Code '{final_code}' provided with force_sync. Queuing background sync.")
                 sync_required = True
                 final_summary = format_parcel_item(final_code, clean_desc)
            
            elif self._has_config_key:
                # Code manually provided - Tracking only (Manual input = No BLE Sync)
                _LOGGER.debug(f"Code '{final_code}' manually provided. Item tracking only (No BLE sync).")
                final_summary = format_parcel_item(final_code, clean_desc)
            
            else: # No key
                 final_summary = format_parcel_item(final_code, clean_desc)
            
        else: # No code provided
            if not self._has_config_key:
                # Degraded: Generate for tracking only
                final_code = generate_random_code()
                final_summary = format_parcel_item(final_code, clean_desc)
                _LOGGER.info(f"Degraded Mode: No Config Key. Generated code '{final_code}' for tracking only.")
            
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
            _LOGGER.warning(f"Could not find todo item with UID {item_uid} to update description")
        except Exception as e:
            _LOGGER.error(f"Failed to update todo item description and metadata: {e}")

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update a todo item."""
        _LOGGER.debug("User requested update of todo item UID: %s, Changes: summary=%s, status=%s", item.uid, item.summary, item.status)
        # Find the existing item
        try:
            existing_index = next(i for i, x in enumerate(self._items) if x.uid == item.uid)
        except StopIteration:
            raise HomeAssistantError("Item not found")

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
                                _LOGGER.info(f"Code changed manually from {old_code} to {new_code}. Removing pending sync for {old_code}.")
                                raw_item.pop("pending_sync_code", None)
                            break
                  
                  if new_code and self._has_config_key:
                       _LOGGER.debug(f"Code changed to '{new_code}' in '{item.summary}'. Item tracking updated (No BLE sync for manual update).")

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

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated logs to auto-complete items."""
        _LOGGER.debug("Coordinator update received, checking for parcel deliveries in latest logs.")
        latest_logs = self.coordinator.data.get("latest_logs")
        _LOGGER.debug("Latest logs content: %s", latest_logs)

        if latest_logs:
            changed = False
            _LOGGER.debug("Processing %d log entries", len(latest_logs))
            for log in latest_logs:
                _LOGGER.debug("Processing log entry: %s", log)
                # Check if this is a code usage event
                event_type = log.get("event_type", "")
                _LOGGER.debug("Log event type: %s", event_type)
                if event_type in ("code_ble_valid", "code_key_valid"):
                    # Get the code from the log entry (now at top level, not in extra_data)
                    used_code = log.get("code")
                    _LOGGER.debug("Found valid code event. Used code: %s", used_code)

                    if used_code:
                        _LOGGER.debug("Checking %d todo items for matching code", len(self._items))
                        # Check all pending items for a matching code
                        for item in self._items:
                            _LOGGER.debug("Checking item UID: %s, Summary: %s, Status: %s", item.uid, item.summary, item.status)
                            if item.status == TodoItemStatus.NEEDS_ACTION:
                                # Parse the code from the item's summary
                                item_code, description = parse_parcel_string(item.summary)
                                _LOGGER.debug("Item code: %s, Used code: %s", item_code, used_code)

                                if item_code and item_code == used_code:
                                    _LOGGER.info(f"Parcel {used_code} delivered! Marking as completed.")
                                    item.status = TodoItemStatus.COMPLETED
                                    # Update raw data to match the updated item
                                    for raw_item in self._raw_data:
                                        if raw_item["uid"] == item.uid:
                                            raw_item["status"] = item.status
                                            break
                                    changed = True

                                    _LOGGER.debug("Fire %s event : %s %s",EVENT_PARCEL_COMPLETED, item_code, description)
                                    # Fire a Home Assistant event
                                    from datetime import datetime
                                    self.hass.bus.async_fire(EVENT_PARCEL_COMPLETED, {
                                        "code": item_code,
                                        "description": description,
                                        "timestamp": datetime.now().isoformat()
                                    })
                                else:
                                    _LOGGER.debug("No match for item. Item code: %s, Used code: %s", item_code, used_code)
                            else:
                                _LOGGER.debug("Item status is not NEEDS_ACTION, skipping. Status: %s", item.status)
                    else:
                        _LOGGER.debug("No used code found in log entry")
                else:
                    _LOGGER.debug("Log event type is not code_ble_valid or code_key_valid, skipping")

            if changed:
                self.hass.async_create_task(self._async_save())
                _LOGGER.debug("Auto-completed todo items based on log entries")
                self.async_write_ha_state()
            else:
                _LOGGER.debug("No items were changed based on log entries")
        else:
            _LOGGER.debug("No latest logs found in coordinator data")

        super()._handle_coordinator_update()