"""Todo platform for Boks."""
import logging
import voluptuous as vol
import uuid
from typing import cast

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
from homeassistant.util import slugify
from homeassistant.helpers.storage import Store
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, EVENT_LOG, CONF_CONFIG_KEY, EVENT_PARCEL_COMPLETED
from .coordinator import BoksDataUpdateCoordinator
from .parcels.utils import parse_parcel_string, generate_random_code, format_parcel_item

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY_TEMPLATE = "boks_parcels_{}"

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

    _attr_has_entity_name = True
    _attr_name = "Suivi Boks" # Clean name override
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
    )

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
        self._attr_unique_id = f"{entry.entry_id}_parcels"
        self._items: list[TodoItem] = []
        self._raw_data = []
        self._has_config_key = has_config_key

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

        # Recovery mechanism: Iterate through self._items
        # If any item has generation_status="pending", re-queue the _async_create_code_background task for it
        if self._has_config_key:
            for item in self._items:
                metadata = self._get_item_metadata(item.uid)
                if metadata.get("generation_status") == "pending":
                    _LOGGER.info(f"Re-queuing code generation for pending item UID: {item.uid}")
                    self.hass.async_create_task(self._async_create_code_background(item.uid))

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
        _LOGGER.debug("User requested creation of todo item: %s", item.summary)
        _LOGGER.debug("Config key available: %s", self._has_config_key)
        # 1. Parse input
        user_input_original = item.summary # Keep original input for degraded mode logging
        code, description = parse_parcel_string(user_input_original)

        _LOGGER.debug("Parsed input - Code: %s, Description: %s", code, description)

        # Build a set of existing active codes for uniqueness check
        existing_active_codes = set()
        for existing in self._items:
             if existing.status == TodoItemStatus.NEEDS_ACTION:
                 c, _ = parse_parcel_string(existing.summary)
                 if c:
                     existing_active_codes.add(c)

        # 2. Logic: Generate code if missing AND we have a config key
        if not code and self._has_config_key:
            _LOGGER.debug("No code provided, will generate one in background")
            # We'll generate the code in the background task
            pass
        elif code and code in existing_active_codes: # Manual code check
            raise HomeAssistantError(f"Code {code} is already used by another active parcel.")
        elif not code and not self._has_config_key:
            _LOGGER.info(f"Degraded Mode: No code provided for '{user_input_original}' and no Config Key available. Item will be for manual tracking.")
        # If code is provided and is unique, we'll use it

        # Determine final summary - store as summary="toto" with metadata generation_status="pending"
        # For async implementation, we store the clean summary and use metadata for status
        final_summary = user_input_original  # Store original text as summary
        _LOGGER.debug("Final summary: %s", final_summary)

        # 5. Update local list immediately (don't wait for BLE)
        new_item = TodoItem(
            uid=uuid.uuid4().hex,
            summary=final_summary,  # Store original text as summary
            status=TodoItemStatus.NEEDS_ACTION,
        )
        self._items.append(new_item)

        # Add metadata for generation status
        raw_item = {
            "uid": new_item.uid,
            "summary": final_summary,
            "status": new_item.status,
        }
        if self._has_config_key:
            raw_item["generation_status"] = "pending"
        self._raw_data.append(raw_item)

        _LOGGER.debug("Added new todo item with UID: %s, Summary: %s", new_item.uid, new_item.summary)
        await self._async_save()
        self.async_write_ha_state()

        # 4. BLE Action: Add Code to Boks (Only if Config Key is present)
        # This is now done asynchronously in the background
        if self._has_config_key:
            self.hass.async_create_task(self._async_create_code_background(new_item.uid))
        elif code and not self._has_config_key:
             _LOGGER.warning(f"Degraded Mode: Code '{code}' parsed from '{user_input_original}' but NOT synced to Boks (No Config Key).")
        elif not code and not self._has_config_key:
             _LOGGER.info(f"Degraded Mode: No code generated or parsed for '{user_input_original}'. Item will be for manual tracking.")
        # if not code and self._has_config_key, this branch should mean no code was provided by user, and generation will happen in background.

    async def _async_create_code_background(self, item_uid: str) -> None:
        """Background task to create the PIN code on the Boks device."""
        try:
            # Retrieve the item by UID
            existing_item = next(x for x in self._items if x.uid == item_uid)
            original_text = existing_item.summary

            # Check if the text already contains a code (using regex)
            code, description = parse_parcel_string(original_text)

            # If no code, generate one
            if not code:
                # Build a set of existing active codes for uniqueness check
                existing_active_codes = set()
                for item in self._items:
                    if item.status == TodoItemStatus.NEEDS_ACTION and item.uid != item_uid:
                        c, _ = parse_parcel_string(item.summary)
                        if c:
                            existing_active_codes.add(c)

                # Generate a unique code
                attempts = 0
                while attempts < 10:
                    code = generate_random_code()
                    _LOGGER.debug("Generated code attempt %d: %s", attempts, code)
                    if code not in existing_active_codes:
                        break
                    attempts += 1
                if code in existing_active_codes:
                    _LOGGER.error("Failed to generate a unique code after multiple attempts.")
                    raise HomeAssistantError("Failed to generate a unique code after multiple attempts.")
                _LOGGER.debug("Successfully generated unique code: %s", code)

            # Connect and send code to Boks
            await self.coordinator.ble_device.connect()
            _LOGGER.debug(f"Attempting to create parcel code {code} on Boks (background task).")
            await self.coordinator.ble_device.create_pin_code(code, "single")
            _LOGGER.info(f"Created parcel code {code} on Boks (background task).")

            # Update the item's summary to include the generated code
            # Format: "{code} - {original_summary}"
            existing_item = next(x for x in self._items if x.uid == item_uid)
            original_summary = existing_item.summary
            new_summary = f"{code} - {original_summary}"
            await self._update_todo_item_description_and_metadata(item_uid, new_summary, None)
        except Exception as e:
            _LOGGER.error(f"Failed to create code on Boks (background task): {e}")
            # Leave the status as "pending" so it gets retried on the next startup
            # Do NOT change the text to indicate error
            pass
        finally:
            await self.coordinator.ble_device.disconnect()

    async def _update_todo_item_metadata(self, item_uid: str, generation_status: str) -> None:
        """Update a todo item's metadata and save."""
        try:
            # Find the item in raw data
            for item in self._raw_data:
                if item["uid"] == item_uid:
                    item["generation_status"] = generation_status
                    break

            await self._async_save()
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error(f"Failed to update todo item metadata: {e}")


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
        # We just update the status locally. We DO NOT delete the code from Boks.
        # User is responsible for code lifecycle.
        if item.status is not None:
            existing_item.status = item.status

        # Case 2: Summary Change (Renaming)
        if item.summary is not None and item.summary != existing_item.summary:
             old_code, _ = parse_parcel_string(existing_item.summary)
             new_code, new_desc = parse_parcel_string(item.summary)

             if old_code != new_code: # Code has changed (or was added/removed)
                 # Check collision for new code only if it exists
                 if new_code:
                     for existing in self._items:
                         if existing.uid != item.uid and existing.status == TodoItemStatus.NEEDS_ACTION:
                             c, _ = parse_parcel_string(existing.summary)
                             if c == new_code:
                                 raise HomeAssistantError(f"Code {new_code} is already used by another active parcel.")

                 # BLE Sync: Only ADD new code if present and we have key.
                 # We DO NOT delete the old code.
                 if new_code and self._has_config_key:
                     try:
                        await self.coordinator.ble_device.connect()
                        # Add new code
                        _LOGGER.debug(f"Attempting to create new code {new_code} on Boks (Renamed item).")
                        await self.coordinator.ble_device.create_pin_code(new_code, "single")
                        _LOGGER.info(f"Created new code {new_code} on Boks (Renamed item).")

                     except Exception as e:
                         raise HomeAssistantError(f"Failed to update code on Boks: {e}")
                     finally:
                        await self.coordinator.ble_device.disconnect()
                 elif new_code and not self._has_config_key:
                      _LOGGER.warning(f"Degraded Mode: Code change to '{new_code}' for '{item.summary}' not synced to Boks (No Config Key).")


             existing_item.summary = format_parcel_item(new_code, new_desc) # Use description even if no code

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
