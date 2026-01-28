"""Tests for the Boks todo list."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.components.todo import TodoItem, TodoItemStatus
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.storage import Store
from custom_components.boks.todo import BoksParcelTodoList, async_setup_entry
from custom_components.boks.const import DOMAIN, CONF_CONFIG_KEY
from homeassistant.const import CONF_ADDRESS
from custom_components.boks.coordinator import BoksDataUpdateCoordinator


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock(spec=BoksDataUpdateCoordinator)
    coordinator.last_update_success = True
    coordinator.ble_device = MagicMock()
    coordinator.ble_device.connect = AsyncMock()
    coordinator.ble_device.disconnect = AsyncMock()
    coordinator.ble_device.create_pin_code = AsyncMock()
    return coordinator


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.data = {CONF_ADDRESS: "AA:BB:CC:DD:EE:FF", CONF_CONFIG_KEY: "12345678"}
    entry.entry_id = "test_entry_id"
    return entry


@pytest.fixture
def mock_store():
    """Create a mock store."""
    store = MagicMock(spec=Store)
    store.async_load = AsyncMock(return_value=None)
    store.async_save = AsyncMock()
    return store


@pytest.fixture
def todo_list(hass: HomeAssistant, mock_coordinator, mock_config_entry, mock_store):
    """Create a BoksParcelTodoList instance."""
    todo_list = BoksParcelTodoList(mock_coordinator, mock_config_entry, mock_store, True)
    todo_list.hass = hass
    todo_list.entity_id = "todo.boks_parcels"
    todo_list.platform = MagicMock()
    todo_list.platform.platform_name = "boks"
    todo_list.platform.domain = DOMAIN
    return todo_list


async def test_async_setup_entry(hass: HomeAssistant, mock_coordinator, mock_config_entry):
    """Test async_setup_entry function."""
    # Set up hass.data
    hass.data[DOMAIN] = {mock_config_entry.entry_id: mock_coordinator}
    
    # Mock async_add_entities
    async_add_entities = MagicMock()
    
    # Mock store
    with patch("custom_components.boks.todo.Store") as mock_store_class:
        mock_store = MagicMock()
        mock_store.async_load = AsyncMock(return_value=None)
        mock_store_class.return_value = mock_store
        
        await async_setup_entry(hass, mock_config_entry, async_add_entities)
        
        # Verify that async_add_entities was called
        async_add_entities.assert_called_once()


async def test_todo_list_init(hass: HomeAssistant, mock_coordinator, mock_config_entry, mock_store):
    """Test BoksParcelTodoList initialization."""
    todo_list = BoksParcelTodoList(mock_coordinator, mock_config_entry, mock_store, True)
    
    assert todo_list._entry == mock_config_entry
    assert todo_list._store == mock_store
    assert todo_list._attr_unique_id == "AA:BB:CC:DD:EE:FF_parcels"
    assert todo_list._has_config_key is True
    assert todo_list._items == []
    assert todo_list._raw_data == []


async def test_todo_list_device_info(hass: HomeAssistant, todo_list):
    """Test device_info property."""
    device_info = todo_list.device_info
    
    assert device_info is not None
    assert "identifiers" in device_info
    assert (DOMAIN, "AA:BB:CC:DD:EE:FF") in device_info["identifiers"]


async def test_todo_list_suggested_object_id(hass: HomeAssistant, todo_list):
    """Test suggested_object_id property."""
    object_id = todo_list.suggested_object_id
    
    assert object_id == "parcels"


async def test_todo_list_translation_placeholders(hass: HomeAssistant, todo_list):
    """Test translation_placeholders property."""
    placeholders = todo_list.translation_placeholders
    
    assert isinstance(placeholders, dict)
    assert placeholders == {}


async def test_todo_list_todo_items_empty(hass: HomeAssistant, todo_list):
    """Test todo_items property with empty list."""
    items = todo_list.todo_items
    
    assert isinstance(items, list)
    assert len(items) == 0


async def test_todo_list_todo_items_with_items(hass: HomeAssistant, todo_list):
    """Test todo_items property with items."""
    # Add some items
    item1 = TodoItem(uid="1", summary="Test item 1", status=TodoItemStatus.NEEDS_ACTION)
    item2 = TodoItem(uid="2", summary="Test item 2", status=TodoItemStatus.COMPLETED)
    
    todo_list._items = [item1, item2]
    
    items = todo_list.todo_items
    
    assert isinstance(items, list)
    assert len(items) == 2
    assert items[0].uid == "1"
    assert items[0].summary == "Test item 1"
    assert items[0].status == TodoItemStatus.NEEDS_ACTION
    assert items[1].uid == "2"
    assert items[1].summary == "Test item 2"
    assert items[1].status == TodoItemStatus.COMPLETED


async def test_async_load_storage_no_data(hass: HomeAssistant, todo_list):
    """Test async_load_storage with no data."""
    todo_list._store.async_load = AsyncMock(return_value=None)
    
    await todo_list.async_load_storage()
    
    assert todo_list._items == []
    assert todo_list._raw_data == []


async def test_async_load_storage_with_data(hass: HomeAssistant, todo_list):
    """Test async_load_storage with data."""
    test_data = [
        {
            "uid": "1",
            "summary": "Test item 1",
            "status": "needs_action"
        },
        {
            "uid": "2",
            "summary": "Test item 2",
            "status": "completed"
        }
    ]
    
    todo_list._store.async_load = AsyncMock(return_value=test_data)
    
    await todo_list.async_load_storage()
    
    assert len(todo_list._items) == 2
    assert len(todo_list._raw_data) == 2
    assert todo_list._items[0].uid == "1"
    assert todo_list._items[0].summary == "Test item 1"
    assert todo_list._items[0].status == TodoItemStatus.NEEDS_ACTION
    assert todo_list._items[1].uid == "2"
    assert todo_list._items[1].summary == "Test item 2"
    assert todo_list._items[1].status == TodoItemStatus.COMPLETED


async def test_async_create_todo_item(hass: HomeAssistant, todo_list):
    """Test async_create_todo_item."""
    item = TodoItem(uid="1", summary="Test item", status=TodoItemStatus.NEEDS_ACTION)
    
    with patch.object(todo_list, "async_create_parcel", new_callable=AsyncMock) as mock_create_parcel:
        await todo_list.async_create_todo_item(item)
        
        mock_create_parcel.assert_called_once_with("Test item", force_background_sync=False)


async def test_async_create_parcel_with_code_and_config_key(hass: HomeAssistant, todo_list):
    """Test async_create_parcel with code and config key."""
    with patch("custom_components.boks.todo.parse_parcel_string", return_value=("ABC123", "Test parcel")), \
         patch("custom_components.boks.todo.format_parcel_item", return_value="ABC123 Test parcel"), \
         patch.object(todo_list, "_async_save", new_callable=AsyncMock), \
         patch.object(todo_list, "_check_pending_codes", new_callable=AsyncMock):
        
        code = await todo_list.async_create_parcel("ABC123 Test parcel")
        
        assert code == "ABC123"
        assert len(todo_list._items) == 1
        assert len(todo_list._raw_data) == 1
        assert todo_list._items[0].summary == "ABC123 Test parcel"
        assert todo_list._items[0].status == TodoItemStatus.NEEDS_ACTION


async def test_async_create_parcel_without_code_with_config_key(hass: HomeAssistant, todo_list):
    """Test async_create_parcel without code but with config key."""
    with patch("custom_components.boks.todo.parse_parcel_string", return_value=(None, "Test parcel")), \
         patch("custom_components.boks.todo.generate_random_code", return_value="XYZ789"), \
         patch("custom_components.boks.todo.format_parcel_item", return_value="XYZ789 Test parcel"), \
         patch.object(todo_list, "_async_save", new_callable=AsyncMock), \
         patch.object(todo_list, "_check_pending_codes", new_callable=AsyncMock):
        
        code = await todo_list.async_create_parcel("Test parcel")
        
        assert code == "XYZ789"
        assert len(todo_list._items) == 1
        assert len(todo_list._raw_data) == 1
        assert todo_list._items[0].summary == "XYZ789 Test parcel"
        assert todo_list._items[0].status == TodoItemStatus.NEEDS_ACTION
        # Check that pending_sync_code is set
        assert "pending_sync_code" in todo_list._raw_data[0]
        assert todo_list._raw_data[0]["pending_sync_code"] == "XYZ789"


async def test_async_create_parcel_without_code_without_config_key(hass: HomeAssistant, mock_coordinator, mock_config_entry, mock_store):
    """Test async_create_parcel without code and without config key."""
    todo_list = BoksParcelTodoList(mock_coordinator, mock_config_entry, mock_store, False)  # No config key
    todo_list.hass = hass
    todo_list.entity_id = "todo.boks_parcels"
    todo_list.platform = MagicMock()
    todo_list.platform.platform_name = "boks"
    todo_list.platform.domain = DOMAIN
    
    with patch("custom_components.boks.todo.parse_parcel_string", return_value=(None, "Test parcel")), \
         patch("custom_components.boks.todo.generate_random_code", return_value="XYZ789"), \
         patch("custom_components.boks.todo.format_parcel_item", return_value="Test parcel"), \
         patch.object(todo_list, "_async_save", new_callable=AsyncMock):
        
        code = await todo_list.async_create_parcel("Test parcel")
        
        assert code is None
        assert len(todo_list._items) == 1
        assert len(todo_list._raw_data) == 1
        assert todo_list._items[0].summary == "Test parcel"
        assert todo_list._items[0].status == TodoItemStatus.NEEDS_ACTION
        # Check that pending_sync_code is NOT set when no config key
        assert not any("pending_sync_code" in item for item in todo_list._raw_data)


async def test_async_update_todo_item_status_change(hass: HomeAssistant, todo_list):
    """Test async_update_todo_item with status change."""
    # Add an item first
    item = TodoItem(uid="1", summary="Test item", status=TodoItemStatus.NEEDS_ACTION)
    todo_list._items = [item]
    todo_list._raw_data = [{"uid": "1", "summary": "Test item", "status": "needs_action"}]
    
    # Update the item status
    updated_item = TodoItem(uid="1", summary=None, status=TodoItemStatus.COMPLETED)
    
    with patch.object(todo_list, "_async_save", new_callable=AsyncMock):
        await todo_list.async_update_todo_item(updated_item)
        
        assert todo_list._items[0].status == TodoItemStatus.COMPLETED
        assert todo_list._raw_data[0]["status"] == "completed"


async def test_async_update_todo_item_summary_change(hass: HomeAssistant, todo_list):
    """Test async_update_todo_item with summary change."""
    # Add an item first
    item = TodoItem(uid="1", summary="ABC123 Test item", status=TodoItemStatus.NEEDS_ACTION)
    todo_list._items = [item]
    todo_list._raw_data = [{"uid": "1", "summary": "ABC123 Test item", "status": "needs_action"}]
    
    # Update the item summary
    updated_item = TodoItem(uid="1", summary="XYZ789 New item", status=None)
    
    with patch("custom_components.boks.todo.parse_parcel_string", side_effect=[("ABC123", "Test item"), ("XYZ789", "New item")]), \
         patch("custom_components.boks.todo.format_parcel_item", return_value="XYZ789 New item"), \
         patch.object(todo_list, "_async_save", new_callable=AsyncMock):
        
        await todo_list.async_update_todo_item(updated_item)
        
        assert todo_list._items[0].summary == "XYZ789 New item"


async def test_async_update_todo_item_not_found(hass: HomeAssistant, todo_list):
    """Test async_update_todo_item with item not found."""
    item = TodoItem(uid="999", summary="Test item", status=TodoItemStatus.NEEDS_ACTION)
    
    with pytest.raises(Exception):  # HomeAssistantError is expected
        await todo_list.async_update_todo_item(item)


async def test_async_delete_todo_item(hass: HomeAssistant, todo_list):
    """Test async_delete_todo_item."""
    # Add an item first
    item = TodoItem(uid="1", summary="Test item", status=TodoItemStatus.NEEDS_ACTION)
    todo_list._items = [item]
    todo_list._raw_data = [{"uid": "1", "summary": "Test item", "status": "needs_action"}]
    
    with patch.object(todo_list, "_async_save", new_callable=AsyncMock):
        await todo_list.async_delete_todo_item("1")
        
        assert len(todo_list._items) == 0
        assert len(todo_list._raw_data) == 0


async def test_async_delete_todo_item_not_found(hass: HomeAssistant, todo_list):
    """Test async_delete_todo_item with item not found."""
    # Add an item first
    item = TodoItem(uid="1", summary="Test item", status=TodoItemStatus.NEEDS_ACTION)
    todo_list._items = [item]
    todo_list._raw_data = [{"uid": "1", "summary": "Test item", "status": "needs_action"}]
    
    with patch.object(todo_list, "_async_save", new_callable=AsyncMock):
        await todo_list.async_delete_todo_item("999")  # Non-existent UID
        
        # Should not delete anything
        assert len(todo_list._items) == 1
        assert len(todo_list._raw_data) == 1


async def test_async_delete_todo_items(hass: HomeAssistant, todo_list):
    """Test async_delete_todo_items."""
    # Add items first
    item1 = TodoItem(uid="1", summary="Test item 1", status=TodoItemStatus.NEEDS_ACTION)
    item2 = TodoItem(uid="2", summary="Test item 2", status=TodoItemStatus.NEEDS_ACTION)
    todo_list._items = [item1, item2]
    todo_list._raw_data = [
        {"uid": "1", "summary": "Test item 1", "status": "needs_action"},
        {"uid": "2", "summary": "Test item 2", "status": "needs_action"}
    ]
    
    with patch.object(todo_list, "_async_save", new_callable=AsyncMock):
        await todo_list.async_delete_todo_items(["1", "2"])
        
        assert len(todo_list._items) == 0
        assert len(todo_list._raw_data) == 0


async def test_get_item_metadata(hass: HomeAssistant, todo_list):
    """Test _get_item_metadata."""
    # Add an item with metadata
    todo_list._raw_data = [
        {
            "uid": "1",
            "summary": "Test item",
            "status": "needs_action",
            "pending_sync_code": "ABC123",
            "custom_field": "custom_value"
        }
    ]
    
    metadata = todo_list._get_item_metadata("1")
    
    assert "pending_sync_code" in metadata
    assert metadata["pending_sync_code"] == "ABC123"
    assert "custom_field" in metadata
    assert metadata["custom_field"] == "custom_value"
    # Standard fields should not be in metadata
    assert "uid" not in metadata
    assert "summary" not in metadata
    assert "status" not in metadata


async def test_get_item_metadata_not_found(hass: HomeAssistant, todo_list):
    """Test _get_item_metadata with item not found."""
    metadata = todo_list._get_item_metadata("999")
    
    assert isinstance(metadata, dict)
    assert len(metadata) == 0


async def test_update_todo_item_metadata_remove_pending(hass: HomeAssistant, todo_list):
    """Test _update_todo_item_metadata_remove_pending."""
    # Add an item with pending sync code
    todo_list._raw_data = [
        {
            "uid": "1",
            "summary": "Test item",
            "status": "needs_action",
            "pending_sync_code": "ABC123",
            "sync_retry_count": 2
        }
    ]
    
    with patch.object(todo_list, "_async_save", new_callable=AsyncMock):
        await todo_list._update_todo_item_metadata_remove_pending("1")
        
        item = todo_list._raw_data[0]
        assert "pending_sync_code" not in item
        assert "sync_retry_count" not in item


async def test_check_pending_codes_no_pending_items(hass: HomeAssistant, todo_list):
    """Test _check_pending_codes with no pending items."""
    todo_list._raw_data = [
        {
            "uid": "1",
            "summary": "Test item",
            "status": "needs_action"
            # No pending_sync_code
        }
    ]
    
    # Should not raise an exception
    result = await todo_list._check_pending_codes()
    assert result is None


async def test_check_pending_codes_with_pending_items(hass: HomeAssistant, todo_list):
    """Test _check_pending_codes with pending items."""
    # Add an item with pending sync code
    todo_list._raw_data = [
        {
            "uid": "1",
            "summary": "Test item",
            "status": "needs_action",
            "pending_sync_code": "ABC123"
        }
    ]
    # Add to _items as well
    item = TodoItem(uid="1", summary="Test item", status=TodoItemStatus.NEEDS_ACTION)
    todo_list._items = [item]
    
    with patch.object(todo_list.coordinator.ble_device, "connect", new_callable=AsyncMock), \
         patch.object(todo_list.coordinator.ble_device, "create_pin_code", new_callable=AsyncMock), \
         patch.object(todo_list.coordinator.ble_device, "disconnect", new_callable=AsyncMock), \
         patch.object(todo_list, "_update_todo_item_metadata_remove_pending", new_callable=AsyncMock), \
         patch.object(todo_list, "_async_save", new_callable=AsyncMock):
        
        await todo_list._check_pending_codes()
        
        # Verify that the BLE methods were called
        todo_list.coordinator.ble_device.connect.assert_called()
        todo_list.coordinator.ble_device.create_pin_code.assert_called_with("ABC123", "single")
        todo_list.coordinator.ble_device.disconnect.assert_called()


async def test_check_pending_codes_max_retries(hass: HomeAssistant, todo_list):
    """Test _check_pending_codes with max retries reached."""
    # Add an item with max retries
    todo_list._raw_data = [
        {
            "uid": "1",
            "summary": "Test item",
            "status": "needs_action",
            "pending_sync_code": "ABC123",
            "sync_retry_count": 5  # Max retries
        }
    ]
    # Add to _items as well
    item = TodoItem(uid="1", summary="Test item", status=TodoItemStatus.NEEDS_ACTION)
    todo_list._items = [item]
    
    with patch.object(todo_list, "_update_todo_item_metadata_remove_pending", new_callable=AsyncMock):
        await todo_list._check_pending_codes()
        
        # Should have called _update_todo_item_metadata_remove_pending to remove pending status
        todo_list._update_todo_item_metadata_remove_pending.assert_called_with("1")


async def test_handle_log_event_matching_code(hass: HomeAssistant, todo_list):
    """Test _handle_log_event with matching code."""
    # Add an item
    item = TodoItem(uid="1", summary="ABC123 Test item", status=TodoItemStatus.NEEDS_ACTION)
    todo_list._items = [item]
    todo_list._raw_data = [{"uid": "1", "summary": "ABC123 Test item", "status": "needs_action"}]
    
    # Create a mock event
    event = MagicMock()
    event.data = {
        "device_id": "test_entry_id",  # Match the config entry ID
        "logs": [
            {
                "event_type": "code_ble_valid",
                "code": "ABC123"
            }
        ]
    }
    
    with patch("custom_components.boks.todo.parse_parcel_string", return_value=("ABC123", "Test item")), \
         patch.object(todo_list, "_async_save", new_callable=AsyncMock):
        
        # Mock async_fire directly on the bus object if possible, or just ignore it if we don't need to assert it
        # But the error is about read-only attribute.
        # Let's try to mock the bus attribute of hass instead.
        with patch.object(todo_list.hass, "bus", MagicMock()):
            todo_list._handle_log_event(event)
        
        # Verify the item was marked as completed
        assert todo_list._items[0].status == TodoItemStatus.COMPLETED
        assert todo_list._raw_data[0]["status"] == "completed"


async def test_handle_log_event_wrong_device(hass: HomeAssistant, todo_list):
    """Test _handle_log_event with wrong device."""
    # Add an item
    item = TodoItem(uid="1", summary="ABC123 Test item", status=TodoItemStatus.NEEDS_ACTION)
    todo_list._items = [item]
    todo_list._raw_data = [{"uid": "1", "summary": "ABC123 Test item", "status": "needs_action"}]
    
    # Create a mock event with wrong device ID
    event = MagicMock()
    event.data = {
        "device_id": "wrong_device_id",
        "logs": [
            {
                "event_type": "code_ble_valid",
                "code": "ABC123"
            }
        ]
    }
    
    with patch("custom_components.boks.todo.parse_parcel_string", return_value=("ABC123", "Test item")):
        todo_list._handle_log_event(event)
        
        # Verify the item was NOT marked as completed
        assert todo_list._items[0].status == TodoItemStatus.NEEDS_ACTION
        assert todo_list._raw_data[0]["status"] == "needs_action"


async def test_async_added_to_hass_with_config_key(hass: HomeAssistant, todo_list):
    """Test async_added_to_hass with config key."""
    with patch("custom_components.boks.todo.async_track_time_interval") as mock_track:
        await todo_list.async_added_to_hass()
        
        # Verify that the timer was set up
        mock_track.assert_called_once()


async def test_async_added_to_hass_without_config_key(hass: HomeAssistant, mock_coordinator, mock_config_entry, mock_store):
    """Test async_added_to_hass without config key."""
    todo_list = BoksParcelTodoList(mock_coordinator, mock_config_entry, mock_store, False)  # No config key
    todo_list.hass = hass
    todo_list.entity_id = "todo.boks_parcels"
    todo_list.platform = MagicMock()
    todo_list.platform.platform_name = "boks"
    todo_list.platform.domain = DOMAIN
    
    with patch("custom_components.boks.todo.async_track_time_interval") as mock_track:
        await todo_list.async_added_to_hass()
        
        # Verify that the timer was NOT set up
        mock_track.assert_not_called()


async def test_async_will_remove_from_hass_with_timer(hass: HomeAssistant, todo_list):
    """Test async_will_remove_from_hass with timer."""
    # Set up a mock timer
    mock_timer = MagicMock()
    todo_list._unsub_timer = mock_timer
    
    await todo_list.async_will_remove_from_hass()
    
    # Verify that the timer was cancelled
    mock_timer.assert_called_once()
    assert todo_list._unsub_timer is None


async def test_async_will_remove_from_hass_without_timer(hass: HomeAssistant, todo_list):
    """Test async_will_remove_from_hass without timer."""
    todo_list._unsub_timer = None
    
    # Should not raise an exception
    await todo_list.async_will_remove_from_hass()