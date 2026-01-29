import logging

from homeassistant.components.todo import TodoItem, TodoItemStatus
from homeassistant.helpers.storage import Store

from ..parcels.utils import parse_parcel_string

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY_TEMPLATE = "boks_parcels_{}"

class BoksParcelStore:
    """Handles storage and data management for Boks parcels."""

    def __init__(self, hass, entry_id: str):
        self._store = Store(
            hass,
            STORAGE_VERSION,
            STORAGE_KEY_TEMPLATE.format(entry_id)
        )
        self._items: list[TodoItem] = []
        self._raw_data: list[dict] = []

    @property
    def items(self) -> list[TodoItem]:
        """Return the list of TodoItems."""
        return self._items

    @property
    def raw_data(self) -> list[dict]:
        """Return the raw data."""
        return self._raw_data

    async def load(self) -> None:
        """Load data from storage and perform migration if needed."""
        data = await self._store.async_load()
        if data:
            self._raw_data = data
            self._items = [
                TodoItem(
                    uid=item["uid"],
                    summary=item["summary"],
                    status=TodoItemStatus(item["status"]),
                    due=item.get("due"),
                    description=item.get("description"),
                )
                for item in data
            ]

            # Migration: Ensure all items have cached parcel_code
            if await self._migrate_data():
                await self.save()
        else:
            self._raw_data = []
            self._items = []

    async def _migrate_data(self) -> bool:
        """Migrate data to ensure parcel_code exists."""
        changed = False
        for item in self._raw_data:
            if "parcel_code" not in item:
                code, _ = parse_parcel_string(item["summary"])
                item["parcel_code"] = code
                changed = True

        if changed:
            _LOGGER.info("Migrated items to include cached parcel codes.")
        return changed

    async def save(self) -> None:
        """Persist data to storage."""
        await self._store.async_save(self._raw_data)

    def get_item(self, uid: str) -> TodoItem | None:
        """Get a TodoItem by UID."""
        for item in self._items:
            if item.uid == uid:
                return item
        return None

    def get_raw_item(self, uid: str) -> dict | None:
        """Get raw item data by UID."""
        for item in self._raw_data:
            if item["uid"] == uid:
                return item
        return None

    def get_items_by_code(self, code: str) -> list[dict]:
        """Get raw items matching a specific parcel code."""
        return [item for item in self._raw_data if item.get("parcel_code") == code]

    async def add_item(self, item: TodoItem, metadata: dict = None) -> None:
        """Add a new item."""
        self._items.append(item)

        raw_item = {
            "uid": item.uid,
            "summary": item.summary,
            "status": item.status,
            "due": item.due,
            "description": item.description,
        }
        if metadata:
            raw_item.update(metadata)

        # Ensure parcel_code is set if not provided in metadata
        if "parcel_code" not in raw_item:
             code, _ = parse_parcel_string(item.summary)
             raw_item["parcel_code"] = code

        self._raw_data.append(raw_item)
        await self.save()

    async def update_item(self, item: TodoItem) -> None:
        """Update an existing item."""
        # Find index
        idx = next((i for i, x in enumerate(self._items) if x.uid == item.uid), -1)
        if idx == -1:
            return

        self._items[idx] = item

        # Update raw data
        for raw_item in self._raw_data:
            if raw_item["uid"] == item.uid:
                raw_item["summary"] = item.summary
                raw_item["status"] = item.status
                raw_item["due"] = item.due
                raw_item["description"] = item.description

                # Update parcel_code cache if summary changed
                code, _ = parse_parcel_string(item.summary)
                raw_item["parcel_code"] = code
                break

        await self.save()

    async def delete_items(self, uids: list[str]) -> None:
        """Delete items by UID."""
        self._items = [x for x in self._items if x.uid not in uids]
        self._raw_data = [x for x in self._raw_data if x["uid"] not in uids]
        await self.save()

    async def move_item(self, uid: str, previous_uid: str | None) -> None:
        """Move an item to a new position."""
        # Find the item to move
        item_idx = next((i for i, x in enumerate(self._items) if x.uid == uid), -1)
        raw_idx = next((i for i, x in enumerate(self._raw_data) if x["uid"] == uid), -1)

        if item_idx == -1 or raw_idx == -1:
            return

        item = self._items.pop(item_idx)
        raw_item = self._raw_data.pop(raw_idx)

        if previous_uid is None:
            # Move to top
            self._items.insert(0, item)
            self._raw_data.insert(0, raw_item)
        else:
            # Find new position
            new_item_idx = next((i for i, x in enumerate(self._items) if x.uid == previous_uid), -1)
            new_raw_idx = next((i for i, x in enumerate(self._raw_data) if x["uid"] == previous_uid), -1)

            if new_item_idx != -1:
                self._items.insert(new_item_idx + 1, item)
            else:
                self._items.append(item)

            if new_raw_idx != -1:
                self._raw_data.insert(new_raw_idx + 1, raw_item)
            else:
                self._raw_data.append(raw_item)

        await self.save()

    async def update_raw_item(self, uid: str, updates: dict) -> None:
        """Update specific fields in raw data (for internal metadata updates)."""
        changed = False
        for raw_item in self._raw_data:
            if raw_item["uid"] == uid:
                raw_item.update(updates)

                # Sync back to TodoItem if standard fields changed
                if "status" in updates or "summary" in updates:
                    for item in self._items:
                        if item.uid == uid:
                            if "status" in updates:
                                item.status = updates["status"]
                            if "summary" in updates:
                                item.summary = updates["summary"]
                            break
                changed = True
                break

        if changed:
            await self.save()

    async def remove_metadata_field(self, uid: str, field: str) -> None:
        """Remove a metadata field from an item."""
        changed = False
        for raw_item in self._raw_data:
            if raw_item["uid"] == uid and field in raw_item:
                raw_item.pop(field)
                changed = True
                break

        if changed:
            await self.save()
