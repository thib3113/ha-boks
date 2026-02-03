import asyncio
import logging
import uuid
from datetime import timedelta

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from ..const import DOMAIN, EVENT_LOGS_RETRIEVED, EVENT_PARCEL_COMPLETED
from ..coordinator import BoksDataUpdateCoordinator
from ..parcels.utils import format_parcel_item, generate_random_code, parse_parcel_string
from .storage import BoksParcelStore

_LOGGER = logging.getLogger(__name__)

# Sync interval for pending codes
SYNC_INTERVAL = timedelta(minutes=1)

class BoksParcelTodoList(CoordinatorEntity, TodoListEntity):
    """A Boks Todo List to manage Parcels and Codes."""

    _attr_has_entity_name = True
    _attr_translation_key = "parcels"
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.MOVE_TODO_ITEM
        | TodoListEntityFeature.SET_DUE_DATE_ON_ITEM
        | TodoListEntityFeature.SET_DUE_DATETIME_ON_ITEM
        | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
    )

    def __init__(
        self,
        coordinator: BoksDataUpdateCoordinator,
        entry: ConfigEntry,
        store: BoksParcelStore,
        has_config_key: bool
    ) -> None:
        """Initialize the Todo List."""
        super().__init__(coordinator)
        self._entry = entry
        self._store = store
        self._attr_unique_id = f"{entry.data[CONF_ADDRESS]}_parcels"
        self._has_config_key = has_config_key
        self._unsub_timer = None

    @property
    def translation_placeholders(self) -> dict[str, str]:
        """Return the translation placeholders."""
        return {}

    @property
    def suggested_object_id(self) -> str | None:
        """Return the suggested object id."""
        return "parcels"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.data[CONF_ADDRESS])},
        )

    @property
    def todo_items(self) -> list[TodoItem] | None:
        """Return the items in the todo list."""
        return self._store.items

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()

        _LOGGER.debug("Subscribing to log events: %s", EVENT_LOGS_RETRIEVED)
        self.async_on_remove(self.hass.bus.async_listen(EVENT_LOGS_RETRIEVED, self._handle_log_event))

        if self._has_config_key:
            self._unsub_timer = async_track_time_interval(
                self.hass, self._check_pending_codes, SYNC_INTERVAL
            )
            self.hass.async_create_task(self._check_pending_codes())

    async def async_will_remove_from_hass(self) -> None:
        """Handle entity removal."""
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None
        await super().async_will_remove_from_hass()

    async def _handle_log_event(self, event) -> None:
        """Handle new logs received from the device via event bus."""
        try:
            _LOGGER.debug("BoksParcelTodoList received event: %s", event)

            match = False
            event_entry_id = event.data.get("config_entry_id")

            if event_entry_id:
                # Primary Check: Config Entry ID
                if event_entry_id == self._entry.entry_id:
                    match = True
            else:
                # Fallback Check: Device ID (only if config_entry_id is missing)
                event_device_id = event.data.get("device_id")
                if event_device_id:
                     device_registry = dr.async_get(self.hass)
                     device_entry = device_registry.async_get_device(identifiers={(DOMAIN, self._entry.data[CONF_ADDRESS])})
                     if device_entry and event_device_id == device_entry.id:
                         match = True

            if not match:
                _LOGGER.debug(
                    "Ignoring log event: No match found. "
                    "Event config_entry_id=%s vs Self=%s. "
                    "Event device_id=%s.",
                    event_entry_id, self._entry.entry_id, event_device_id
                )
                return

            _LOGGER.debug("Log event matched for entry %s", self._entry.entry_id)

            latest_logs = event.data.get("logs", [])
            if latest_logs:
                changed = False
                for log in latest_logs:
                    # Check if this is a code usage event
                    event_type = log.get("event_type", "")
                    if event_type in ("code_ble_valid", "code_key_valid"):
                        used_code = log.get("code")
                        if used_code:
                            # Use Store to find matching items
                            matching_items = self._store.get_items_by_code(used_code)
                            for raw_item in matching_items:
                                if raw_item["status"] == TodoItemStatus.NEEDS_ACTION:
                                    _LOGGER.info("Parcel %s delivered! Marking as completed.", used_code)

                                    # Update status via Store
                                    await self._store.update_raw_item(raw_item["uid"], {"status": TodoItemStatus.COMPLETED})
                                    changed = True

                                    _, description = parse_parcel_string(raw_item["summary"])
                                    self.hass.bus.async_fire(EVENT_PARCEL_COMPLETED, {
                                        "code": used_code,
                                        "description": description,
                                        "timestamp": dt_util.now().isoformat()
                                    })

                if changed:
                    self.async_write_ha_state()
        except Exception as e:
            _LOGGER.exception("Error handling log event: %s", e)
    async def _check_pending_codes(self, now=None) -> None:
        """Periodic task to sync pending codes to Boks."""
        pending_items = [
            item for item in self._store.raw_data
            if item.get("pending_sync_code")
        ]

        if not pending_items:
            return

        for raw_item in pending_items:
            uid = raw_item["uid"]
            code = raw_item["pending_sync_code"]
            retry_count = raw_item.get("sync_retry_count", 0)

            if retry_count >= 5:
                _LOGGER.warning("Aborting sync for code %s (Item %s) after %d failed attempts.", code, uid, retry_count)
                await self._remove_pending_status(uid)
                continue

            try:
                await self.coordinator.ble_device.connect()
                if not self.coordinator.ble_device.is_connected:
                     break

                await self.coordinator.ble_device.create_pin_code(code, "single")
                _LOGGER.info("Successfully synced pending code %s to Boks.", code)
                await self._remove_pending_status(uid)

            except Exception as e:
                _LOGGER.error("Failed to sync pending code %s: %s", code, e)
                await self._store.update_raw_item(uid, {"sync_retry_count": retry_count + 1})
            finally:
                await asyncio.shield(self.coordinator.ble_device.disconnect())

    async def _remove_pending_status(self, uid: str) -> None:
        """Remove pending status fields."""
        await self._store.remove_metadata_field(uid, "pending_sync_code")
        await self._store.remove_metadata_field(uid, "sync_retry_count")
        await self._store.remove_metadata_field(uid, "generation_status")
        self.async_write_ha_state()

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Add an item to the list."""
        await self.async_create_parcel(
            item.summary,
            force_background_sync=False,
            due=item.due,
            description=item.description
        )

    async def async_create_parcel(
        self,
        summary: str,
        force_background_sync: bool = False,
        due: str | None = None,
        description: str | None = None
    ) -> str | None:
        """Create a parcel item."""
        code, clean_desc = parse_parcel_string(summary)
        final_code = code
        sync_required = False

        if final_code:
            if self._has_config_key and force_background_sync:
                 sync_required = True
                 final_summary = format_parcel_item(final_code, clean_desc)
            else:
                 final_summary = format_parcel_item(final_code, clean_desc)
        else:
            if not self._has_config_key:
                final_code = None
                final_summary = format_parcel_item(final_code, clean_desc)
            else:
                final_code = generate_random_code()
                # Ensure uniqueness
                existing_codes = {
                    item.get("parcel_code") for item in self._store.raw_data
                }
                for _ in range(10):
                    if final_code not in existing_codes:
                        break
                    final_code = generate_random_code()

                final_summary = format_parcel_item(final_code, clean_desc)
                sync_required = True

        new_item = TodoItem(
            uid=uuid.uuid4().hex,
            summary=final_summary,
            status=TodoItemStatus.NEEDS_ACTION,
            due=due,
            description=description
        )

        metadata = {"parcel_code": final_code}
        if sync_required:
            metadata["pending_sync_code"] = final_code

        await self._store.add_item(new_item, metadata)
        self.async_write_ha_state()

        if sync_required:
             self.hass.async_create_task(self._check_pending_codes())

        return final_code

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update a todo item."""
        try:
            existing_item = self._store.get_item(item.uid)
            if not existing_item:
                raise ValueError("Item not found")
        except ValueError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="item_not_found"
            ) from e

        # Handle summary change logic (sync cancellation)
        if item.summary is not None and item.summary != existing_item.summary:
             raw_item = self._store.get_raw_item(item.uid)
             old_code = raw_item.get("parcel_code")
             new_code, new_desc = parse_parcel_string(item.summary)

             if old_code != new_code:
                 if raw_item.get("pending_sync_code"):
                     _LOGGER.info("Code changed manually. Removing pending sync for %s.", old_code)
                     await self._store.remove_metadata_field(item.uid, "pending_sync_code")

             item.summary = format_parcel_item(new_code, new_desc)

        # Merge updates (TodoItem fields are optional/partial in updates)
        if item.status is not None:
            existing_item.status = item.status
        if item.summary is not None:
            existing_item.summary = item.summary
        if item.due is not None:
            existing_item.due = item.due
        if item.description is not None:
            existing_item.description = item.description

        await self._store.update_item(existing_item)
        self.async_write_ha_state()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete todo items."""
        await self._store.delete_items(uids)
        self.async_write_ha_state()

    async def async_move_todo_item(self, uid: str, previous_uid: str | None = None) -> None:
        """Move a todo item to a new position."""
        await self._store.move_item(uid, previous_uid)
        self.async_write_ha_state()
