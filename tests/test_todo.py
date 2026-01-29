"""Tests for the Boks todo list."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.components.todo import TodoItem, TodoItemStatus
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.storage import Store
from custom_components.boks.todo.entity import BoksParcelTodoList
from custom_components.boks.todo.storage import BoksParcelStore
from custom_components.boks.todo import async_setup_entry
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
    coordinator.ble_device.is_connected = True
    return coordinator


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.data = {CONF_ADDRESS: "AA:BB:CC:DD:EE:FF", CONF_CONFIG_KEY: "12345678"}
    entry.entry_id = "test_entry_id"
    return entry


@pytest.fixture
def mock_store_backend():
    """Create a mock HA storage backend."""
    store = MagicMock(spec=Store)
    store.async_load = AsyncMock(return_value=None)
    store.async_save = AsyncMock()
    return store


@pytest.fixture
def store(hass: HomeAssistant, mock_store_backend):
    """Create a BoksParcelStore instance with mocked backend."""
    with patch("custom_components.boks.todo.storage.Store", return_value=mock_store_backend):
        store = BoksParcelStore(hass, "test_entry_id")
        return store


@pytest.fixture
async def loaded_store(store, mock_store_backend):
    """Create a BoksParcelStore that has loaded data."""
    mock_store_backend.async_load.return_value = [
        {"uid": "1", "summary": "Item 1", "status": "needs_action", "parcel_code": "CODE1"},
        {"uid": "2", "summary": "Item 2", "status": "completed", "parcel_code": "CODE2"}
    ]
    await store.load()
    return store


@pytest.fixture
def todo_list(hass: HomeAssistant, mock_coordinator, mock_config_entry, loaded_store):
    """Create a BoksParcelTodoList instance."""
    todo_list = BoksParcelTodoList(mock_coordinator, mock_config_entry, loaded_store, True)
    todo_list.hass = hass
    todo_list.entity_id = "todo.boks_parcels"
    
    # Mock platform for entity naming
    mock_platform = MagicMock()
    mock_platform.platform_name = "boks"
    mock_platform.domain = DOMAIN
    todo_list.platform = mock_platform
    
    return todo_list


async def test_store_load_migration(hass: HomeAssistant, mock_store_backend):
    """Test store load with migration."""
    # Data without parcel_code
    mock_store_backend.async_load.return_value = [
        {"uid": "1", "summary": "ABC1234 Item", "status": "needs_action"}
    ]
    
    with patch("custom_components.boks.todo.storage.Store", return_value=mock_store_backend):
        store = BoksParcelStore(hass, "test_entry_id")
        
        # Mock parsing
        with patch("custom_components.boks.todo.storage.parse_parcel_string", return_value=("ABC1234", "Item")):
            await store.load()
            
            # Check migration happened
            assert len(store.items) == 1
            assert store.raw_data[0]["parcel_code"] == "ABC1234"
            mock_store_backend.async_save.assert_called_once()


async def test_store_crud(hass: HomeAssistant, store, mock_store_backend):
    """Test Store CRUD operations."""
    await store.load()
    
    # Add
    item = TodoItem(
        uid="new", 
        summary="New", 
        status=TodoItemStatus.NEEDS_ACTION, 
        description="Detailed description", 
        due="2026-01-29T22:00:00Z"
    )
    with patch("custom_components.boks.todo.storage.parse_parcel_string", return_value=(None, "New")):
        await store.add_item(item)
    
    assert len(store.items) == 1
    assert store.raw_data[0]["uid"] == "new"
    assert store.raw_data[0]["description"] == "Detailed description"
    assert store.raw_data[0]["due"] == "2026-01-29T22:00:00Z"
    mock_store_backend.async_save.assert_called()
    
    # Update
    item.status = TodoItemStatus.COMPLETED
    item.description = "Updated description"
    await store.update_item(item)
    assert store.items[0].status == TodoItemStatus.COMPLETED
    assert store.items[0].description == "Updated description"
    assert store.raw_data[0]["status"] == TodoItemStatus.COMPLETED
    assert store.raw_data[0]["description"] == "Updated description"
    
    # Delete
    await store.delete_items(["new"])
    assert len(store.items) == 0
    assert len(store.raw_data) == 0


async def test_store_move_item(hass: HomeAssistant, store, mock_store_backend):
    """Test Store move_item operation."""
    # Setup 3 items
    store._items = [
        TodoItem(uid="1", summary="Item 1", status=TodoItemStatus.NEEDS_ACTION),
        TodoItem(uid="2", summary="Item 2", status=TodoItemStatus.NEEDS_ACTION),
        TodoItem(uid="3", summary="Item 3", status=TodoItemStatus.NEEDS_ACTION)
    ]
    store._raw_data = [
        {"uid": "1", "summary": "Item 1", "status": "needs_action"},
        {"uid": "2", "summary": "Item 2", "status": "needs_action"},
        {"uid": "3", "summary": "Item 3", "status": "needs_action"}
    ]
    
    # Move 3 to top
    await store.move_item("3", None)
    assert [i.uid for i in store.items] == ["3", "1", "2"]
    assert [i["uid"] for i in store.raw_data] == ["3", "1", "2"]
    
    # Move 1 after 2
    await store.move_item("1", "2")
    assert [i.uid for i in store.items] == ["3", "2", "1"]
    assert [i["uid"] for i in store.raw_data] == ["3", "2", "1"]


async def test_entity_create_todo_item(hass: HomeAssistant, todo_list):
    """Test creating a todo item via entity."""
    item = TodoItem(
        uid="ignore", 
        summary="ABC1234 Test", 
        status=TodoItemStatus.NEEDS_ACTION,
        description="My Parcel",
        due="2026-12-31"
    )
    
    with (
        patch("custom_components.boks.todo.entity.parse_parcel_string", return_value=("ABC1234", "Test")),
        patch("custom_components.boks.todo.entity.format_parcel_item", return_value="ABC1234 - Test"),
        patch.object(todo_list._store, "add_item", new_callable=AsyncMock) as mock_add
    ):
        
        await todo_list.async_create_todo_item(item)
        
        mock_add.assert_called_once()
        args = mock_add.call_args[0]
        assert args[0].summary == "ABC1234 - Test"
        assert args[0].description == "My Parcel"
        assert args[0].due == "2026-12-31"
        assert args[1]["parcel_code"] == "ABC1234"


async def test_entity_move_todo_item(hass: HomeAssistant, todo_list):
    """Test moving a todo item via entity."""
    with patch.object(todo_list._store, "move_item", new_callable=AsyncMock) as mock_move:
        await todo_list.async_move_todo_item("item_uid", "prev_uid")
        mock_move.assert_called_once_with("item_uid", "prev_uid")


async def test_entity_handle_log_event(hass: HomeAssistant, todo_list):
    """Test log event handling."""
    # Setup matching data in store
    # "1" has code "CODE1" (from fixture)
    
    event = MagicMock()
    event.data = {
        "device_id": "resolved_device_id",
        "logs": [{"event_type": "code_key_valid", "code": "CODE1"}]
    }
    
    # Mock registry lookup
    mock_dr = MagicMock()
    mock_device = MagicMock()
    mock_device.id = "resolved_device_id"
    mock_dr.async_get_device.return_value = mock_device
    
    with (
        patch("custom_components.boks.todo.entity.dr.async_get", return_value=mock_dr),
        patch("custom_components.boks.todo.entity.parse_parcel_string", return_value=("CODE1", "Item 1")),
        patch.object(todo_list.hass, "bus", MagicMock()),
        patch.object(todo_list._store, "update_raw_item", new_callable=AsyncMock) as mock_update
    ):
         
         await todo_list._handle_log_event(event)
         
         mock_update.assert_called_once()
         assert mock_update.call_args[0][0] == "1"
         assert mock_update.call_args[0][1] == {"status": TodoItemStatus.COMPLETED}


async def test_entity_handle_log_event_mismatch(hass: HomeAssistant, todo_list):
    """Test log event with mismatching device ID."""
    event = MagicMock()
    event.data = {"device_id": "wrong_id", "logs": []}
    
    mock_dr = MagicMock()
    mock_device = MagicMock()
    mock_device.id = "correct_id"
    mock_dr.async_get_device.return_value = mock_device
    
    with (
        patch("custom_components.boks.todo.entity.dr.async_get", return_value=mock_dr),
        patch.object(todo_list._store, "update_raw_item", new_callable=AsyncMock) as mock_update
    ):
         
         await todo_list._handle_log_event(event)
         
         mock_update.assert_not_called()


async def test_check_pending_codes(hass: HomeAssistant, todo_list):
    """Test checking pending codes."""
    # Inject pending item into store
    todo_list._store._raw_data.append({
        "uid": "pending",
        "summary": "Pending",
        "status": "needs_action",
        "pending_sync_code": "PENDING"
    })
    
    with (
        patch.object(todo_list.coordinator.ble_device, "connect", new_callable=AsyncMock),
        patch.object(todo_list.coordinator.ble_device, "create_pin_code", new_callable=AsyncMock) as mock_create,
        patch.object(todo_list.coordinator.ble_device, "disconnect", new_callable=AsyncMock),
        patch.object(todo_list, "_remove_pending_status", new_callable=AsyncMock) as mock_remove
    ):
         
         await todo_list._check_pending_codes()
         
         mock_create.assert_called_with("PENDING", "single")
         mock_remove.assert_called_with("pending")