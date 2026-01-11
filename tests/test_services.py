"Tests for the Boks services."
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.boks.services import (
    get_coordinator_from_call,
    async_setup_services,
    SERVICE_ADD_PARCEL_SCHEMA,
    SERVICE_ADD_SINGLE_CODE_SCHEMA,
    SERVICE_DELETE_SINGLE_CODE_SCHEMA,
    SERVICE_ADD_MASTER_CODE_SCHEMA,
    SERVICE_DELETE_MASTER_CODE_SCHEMA,
    SERVICE_SYNC_LOGS_SCHEMA,
    SERVICE_CLEAN_MASTER_CODES_SCHEMA,
    SERVICE_SET_CONFIGURATION_SCHEMA
)
from custom_components.boks.ble.const import BoksConfigType
from custom_components.boks.const import DOMAIN, CONF_CONFIG_KEY
from custom_components.boks.coordinator import BoksDataUpdateCoordinator
from custom_components.boks.errors import BoksError
from custom_components.boks.todo import BoksParcelTodoList


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {
        DOMAIN: {},
        "entity_components": {}
    }
    hass.services = MagicMock()
    hass.services.async_register = MagicMock()
    return hass


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock(spec=BoksDataUpdateCoordinator)
    coordinator.maintenance_status = {"running": False}
    coordinator.data = {}
    coordinator.ble_device = MagicMock()
    coordinator.ble_device.connect = AsyncMock()
    coordinator.ble_device.disconnect = AsyncMock()
    coordinator.ble_device.create_pin_code = AsyncMock(return_value="ABC123")
    coordinator.ble_device.delete_pin_code = AsyncMock(return_value=True)
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_sync_logs = AsyncMock()
    return coordinator


@pytest.fixture
def mock_service_call():
    """Create a mock service call."""
    call = MagicMock(spec=ServiceCall)
    call.data = {}
    return call


def test_get_coordinator_from_call_device_id_found(mock_hass, mock_coordinator):
    """Test get_coordinator_from_call with device ID found."""
    # Set up hass.data with a coordinator
    entry_id = "test_entry_id"
    mock_hass.data[DOMAIN] = {entry_id: mock_coordinator}
    
    # Set up device registry
    mock_device_registry = MagicMock()
    mock_device = MagicMock()
    mock_device.config_entries = [entry_id]
    mock_device_registry.async_get.return_value = mock_device
    with patch("homeassistant.helpers.device_registry.async_get", return_value=mock_device_registry):
        # Create a mock service call with device_id
        call = MagicMock()
        call.data = {"device_id": "test_device_id"}
        
        coordinator = get_coordinator_from_call(mock_hass, call)
        
        assert coordinator == mock_coordinator


def test_get_coordinator_from_call_device_id_not_found(mock_hass):
    """Test get_coordinator_from_call with device ID not found."""
    # Set up device registry to return None
    mock_device_registry = MagicMock()
    mock_device_registry.async_get.return_value = None
    with patch("homeassistant.helpers.device_registry.async_get", return_value=mock_device_registry):
        # Create a mock service call with device_id
        call = MagicMock()
        call.data = {"device_id": "test_device_id"}
        
        with pytest.raises(HomeAssistantError) as excinfo:
            get_coordinator_from_call(mock_hass, call)
        assert excinfo.value.translation_key == "target_devices_not_boks"


def test_get_coordinator_from_call_entity_id_found(mock_hass, mock_coordinator):
    """Test get_coordinator_from_call with entity ID found."""
    # Set up hass.data with a coordinator
    entry_id = "test_entry_id"
    mock_hass.data[DOMAIN] = {entry_id: mock_coordinator}
    
    # Set up entity registry
    mock_entity_registry = MagicMock()
    mock_entry = MagicMock()
    mock_entry.config_entry_id = entry_id
    mock_entity_registry.async_get.return_value = mock_entry
    with patch("homeassistant.helpers.entity_registry.async_get", return_value=mock_entity_registry):
        # Create a mock service call with entity_id
        call = MagicMock()
        call.data = {"entity_id": "test_entity_id"}
        
        coordinator = get_coordinator_from_call(mock_hass, call)
        
        assert coordinator == mock_coordinator


def test_get_coordinator_from_call_entity_id_not_found(mock_hass):
    """Test get_coordinator_from_call with entity ID not found."""
    # Set up entity registry to return None
    mock_entity_registry = MagicMock()
    mock_entity_registry.async_get.return_value = None
    with patch("homeassistant.helpers.entity_registry.async_get", return_value=mock_entity_registry):
        # Create a mock service call with entity_id
        call = MagicMock()
        call.data = {"entity_id": "test_entity_id"}
        
        with pytest.raises(HomeAssistantError) as excinfo:
            get_coordinator_from_call(mock_hass, call)
        assert excinfo.value.translation_key == "target_entities_not_boks"


def test_get_coordinator_from_call_single_instance_found(mock_hass, mock_coordinator):
    """Test get_coordinator_from_call with single instance found."""
    # Set up hass.data with a single coordinator
    mock_hass.data[DOMAIN] = {"test_entry_id": mock_coordinator}
    
    # Create a mock service call with no targets
    call = MagicMock()
    call.data = {}
    
    coordinator = get_coordinator_from_call(mock_hass, call)
    
    assert coordinator == mock_coordinator


def test_get_coordinator_from_call_single_instance_not_found(mock_hass):
    """Test get_coordinator_from_call with single instance not found."""
    # Set up hass.data with no coordinators
    mock_hass.data[DOMAIN] = {}
    
    # Create a mock service call with no targets
    call = MagicMock()
    call.data = {}
    
    with pytest.raises(HomeAssistantError) as excinfo:
        get_coordinator_from_call(mock_hass, call)
    assert excinfo.value.translation_key == "target_device_missing"


def test_get_coordinator_from_call_multiple_instances(mock_hass, mock_coordinator):
    """Test get_coordinator_from_call with multiple instances."""
    # Set up hass.data with multiple coordinators
    mock_hass.data[DOMAIN] = {
        "test_entry_id_1": mock_coordinator,
        "test_entry_id_2": mock_coordinator
    }
    
    # Create a mock service call with no targets
    call = MagicMock()
    call.data = {}
    
    with pytest.raises(HomeAssistantError) as excinfo:
        get_coordinator_from_call(mock_hass, call)
    assert excinfo.value.translation_key == "target_device_missing"


async def test_async_setup_services(mock_hass):
    """Test async_setup_services."""
    with patch("custom_components.boks.services.cv") as mock_cv:
        # Mock the schema validation functions
        mock_cv.string = MagicMock()
        mock_cv.positive_int = MagicMock()
        mock_cv.In = MagicMock()
        
        await async_setup_services(mock_hass)
        
        # Verify that services were registered (there are 11 services now)
        assert mock_hass.services.async_register.call_count == 11

async def test_handle_add_parcel_with_entity_id(mock_hass, mock_coordinator):
    """Test handle_add_parcel service with entity_id."""
    # Set up the service call
    call = MagicMock()
    call.data = {"entity_id": "test_entity_id", "description": "Test parcel"}
    
    # Set up entity registry
    mock_entity_registry = MagicMock()
    mock_entry = MagicMock()
    mock_entry.config_entry_id = "test_entry_id"
    mock_entity_registry.async_get.return_value = mock_entry
    with patch("homeassistant.helpers.entity_registry.async_get", return_value=mock_entity_registry):
        # Set up entity component
        mock_component = MagicMock()
        mock_todo_entity = MagicMock(spec=BoksParcelTodoList)
        mock_todo_entity._has_config_key = True
        mock_todo_entity.async_create_parcel = AsyncMock()
        mock_component.get_entity.return_value = mock_todo_entity
        mock_hass.data["entity_components"]["todo"] = mock_component
        
        # Capture handler
        handlers = {}
        mock_hass.services.async_register.side_effect = lambda d, s, h, **k: handlers.update({s: h})
        await async_setup_services(mock_hass)
        handler = handlers["add_parcel"]
        
        with (
            patch("custom_components.boks.services.parse_parcel_string", return_value=(None, "Test parcel")),
            patch("custom_components.boks.services.generate_random_code", return_value="ABC123"), 
            patch("custom_components.boks.services.format_parcel_item", return_value="ABC123 Test parcel")
        ):
            
            result = await handler(call)
            
            assert result == {"code": "ABC123"}
            mock_todo_entity.async_create_parcel.assert_called_once_with("ABC123 Test parcel", force_background_sync=True)


async def test_handle_add_parcel_with_device_id(mock_hass, mock_coordinator):
    """Test handle_add_parcel service with device_id."""
    # Set up the service call
    call = MagicMock()
    call.data = {"device_id": "test_device_id", "description": "Test parcel"}
    
    # Set up entity registry
    mock_entity_registry = MagicMock()
    mock_entry = MagicMock()
    mock_entry.device_id = "test_device_id"
    mock_entry.domain = "todo"
    mock_entry.entity_id = "test_entity_id"
    mock_entity_registry.entities.values.return_value = [mock_entry]
    with patch("homeassistant.helpers.entity_registry.async_get", return_value=mock_entity_registry):
        # Set up entity component
        mock_component = MagicMock()
        mock_todo_entity = MagicMock(spec=BoksParcelTodoList)
        mock_todo_entity._has_config_key = True
        mock_todo_entity.async_create_parcel = AsyncMock()
        mock_component.get_entity.return_value = mock_todo_entity
        mock_hass.data["entity_components"]["todo"] = mock_component
        
        # Capture handler
        handlers = {}
        mock_hass.services.async_register.side_effect = lambda d, s, h, **k: handlers.update({s: h})
        await async_setup_services(mock_hass)
        handler = handlers["add_parcel"]
        
        with (
            patch("custom_components.boks.services.parse_parcel_string", return_value=(None, "Test parcel")),
            patch("custom_components.boks.services.generate_random_code", return_value="ABC123"), 
            patch("custom_components.boks.services.format_parcel_item", return_value="ABC123 Test parcel")
        ):
            
            result = await handler(call)
            
            assert result == {"code": "ABC123"}
            mock_todo_entity.async_create_parcel.assert_called_once_with("ABC123 Test parcel", force_background_sync=True)


async def test_handle_add_parcel_no_targets_single_instance(mock_hass, mock_coordinator):
    """Test handle_add_parcel service with no targets but single instance."""
    # Set up hass.data with a single coordinator
    entry_id = "test_entry_id"
    mock_hass.data[DOMAIN] = {entry_id: mock_coordinator, "translations": {}}
    
    # Set up the service call
    call = MagicMock()
    call.data = {"description": "Test parcel"}
    
    # Set up entity registry
    mock_entity_registry = MagicMock()
    mock_entry = MagicMock()
    mock_entry.config_entry_id = entry_id
    mock_entry.domain = "todo"
    mock_entry.entity_id = "test_entity_id"
    mock_entity_registry.entities.values.return_value = [mock_entry]
    with patch("homeassistant.helpers.entity_registry.async_get", return_value=mock_entity_registry):
        # Set up entity component
        mock_component = MagicMock()
        mock_todo_entity = MagicMock(spec=BoksParcelTodoList)
        mock_todo_entity._has_config_key = True
        mock_todo_entity.async_create_parcel = AsyncMock()
        mock_component.get_entity.return_value = mock_todo_entity
        mock_hass.data["entity_components"]["todo"] = mock_component
        
        # Capture handler
        handlers = {}
        mock_hass.services.async_register.side_effect = lambda d, s, h, **k: handlers.update({s: h})
        await async_setup_services(mock_hass)
        handler = handlers["add_parcel"]
        
        with (
            patch("custom_components.boks.services.parse_parcel_string", return_value=(None, "Test parcel")),
            patch("custom_components.boks.services.generate_random_code", return_value="ABC123"), 
            patch("custom_components.boks.services.format_parcel_item", return_value="ABC123 Test parcel")
        ):
            
            result = await handler(call)
            
            assert result == {"code": "ABC123"}
            mock_todo_entity.async_create_parcel.assert_called_once_with("ABC123 Test parcel", force_background_sync=True)


async def test_handle_add_parcel_todo_entity_not_found(mock_hass):
    """Test handle_add_parcel service when todo entity is not found."""
    # Set up the service call
    call = MagicMock()
    call.data = {"entity_id": "test_entity_id", "description": "Test parcel"}
    
    # Set up entity registry
    mock_entity_registry = MagicMock()
    mock_entry = MagicMock()
    mock_entry.config_entry_id = "test_entry_id"
    mock_entity_registry.async_get.return_value = mock_entry
    with patch("homeassistant.helpers.entity_registry.async_get", return_value=mock_entity_registry):
        # Set up entity component to return None
        mock_component = MagicMock()
        mock_component.get_entity.return_value = None
        mock_hass.data["entity_components"]["todo"] = mock_component
        
        # Capture handler
        handlers = {}
        mock_hass.services.async_register.side_effect = lambda d, s, h, **k: handlers.update({s: h})
        await async_setup_services(mock_hass)
        handler = handlers["add_parcel"]
        
        with pytest.raises(HomeAssistantError) as excinfo:
            await handler(call)
        assert excinfo.value.translation_key == "todo_entity_not_found"


async def test_handle_add_single_code_success(mock_hass, mock_coordinator):
    """Test handle_add_single_code service success."""
    # Set up hass.data with a coordinator
    entry_id = "test_entry_id"
    mock_hass.data[DOMAIN] = {entry_id: mock_coordinator}
    
    # Set up the service call
    call = MagicMock()
    call.data = {"code": "ABC123"}
    
    # Capture handler
    handlers = {}
    mock_hass.services.async_register.side_effect = lambda d, s, h, **k: handlers.update({s: h})
    await async_setup_services(mock_hass)
    handler = handlers["add_single_code"]
    
    with patch("custom_components.boks.services.get_coordinator_from_call", return_value=mock_coordinator):
        result = await handler(call)
        
        assert result == {"code": "ABC123"}
        mock_coordinator.ble_device.connect.assert_called()
        mock_coordinator.ble_device.create_pin_code.assert_called_with("ABC123", "single", 0)
        mock_coordinator.ble_device.disconnect.assert_called()


async def test_handle_add_single_code_boks_error(mock_hass, mock_coordinator):
    """Test handle_add_single_code service with BoksError."""
    # Set up hass.data with a coordinator
    entry_id = "test_entry_id"
    mock_hass.data[DOMAIN] = {entry_id: mock_coordinator}
    
    # Set up the service call
    call = MagicMock()
    call.data = {"code": "ABC123"}
    
    # Make create_pin_code raise a BoksError
    mock_coordinator.ble_device.create_pin_code.side_effect = BoksError("test_error")
    
    # Capture handler
    handlers = {}
    mock_hass.services.async_register.side_effect = lambda d, s, h, **k: handlers.update({s: h})
    await async_setup_services(mock_hass)
    handler = handlers["add_single_code"]
    
    with patch("custom_components.boks.services.get_coordinator_from_call", return_value=mock_coordinator):
        with pytest.raises(HomeAssistantError):
            await handler(call)


async def test_handle_delete_single_code_success(mock_hass, mock_coordinator):
    """Test handle_delete_single_code service success."""
    # Set up hass.data with a coordinator
    entry_id = "test_entry_id"
    mock_hass.data[DOMAIN] = {entry_id: mock_coordinator}
    
    # Set up the service call
    call = MagicMock()
    call.data = {"code": "ABC123"}
    
    # Capture handler
    handlers = {}
    mock_hass.services.async_register.side_effect = lambda d, s, h, **k: handlers.update({s: h})
    await async_setup_services(mock_hass)
    handler = handlers["delete_single_code"]
    
    with patch("custom_components.boks.services.get_coordinator_from_call", return_value=mock_coordinator):
        await handler(call)
        
        mock_coordinator.ble_device.connect.assert_called()
        mock_coordinator.ble_device.delete_pin_code.assert_called_with("single", "ABC123")
        mock_coordinator.ble_device.disconnect.assert_called()


async def test_handle_delete_single_code_boks_error(mock_hass, mock_coordinator):
    """Test handle_delete_single_code service with BoksError."""
    # Set up hass.data with a coordinator
    entry_id = "test_entry_id"
    mock_hass.data[DOMAIN] = {entry_id: mock_coordinator}
    
    # Set up the service call
    call = MagicMock()
    call.data = {"code": "ABC123"}
    
    # Make delete_pin_code raise a BoksError
    mock_coordinator.ble_device.delete_pin_code.side_effect = BoksError("test_error")
    
    # Capture handler
    handlers = {}
    mock_hass.services.async_register.side_effect = lambda d, s, h, **k: handlers.update({s: h})
    await async_setup_services(mock_hass)
    handler = handlers["delete_single_code"]
    
    with patch("custom_components.boks.services.get_coordinator_from_call", return_value=mock_coordinator):
        with pytest.raises(HomeAssistantError):
            await handler(call)


async def test_handle_sync_logs_success(mock_hass, mock_coordinator):
    """Test handle_sync_logs service success."""
    # Set up hass.data with a coordinator
    entry_id = "test_entry_id"
    mock_hass.data[DOMAIN] = {entry_id: mock_coordinator}
    
    # Set up the service call
    call = MagicMock()
    call.data = {}
    
    # Capture handler
    handlers = {}
    mock_hass.services.async_register.side_effect = lambda d, s, h, **k: handlers.update({s: h})
    await async_setup_services(mock_hass)
    handler = handlers["sync_logs"]
    
    with patch("custom_components.boks.services.get_coordinator_from_call", return_value=mock_coordinator):
        await handler(call)
        
        mock_coordinator.async_sync_logs.assert_called_once_with(update_state=True)


async def test_handle_sync_logs_exception(mock_hass, mock_coordinator):
    """Test handle_sync_logs service with exception."""
    # Set up hass.data with a coordinator
    entry_id = "test_entry_id"
    mock_hass.data[DOMAIN] = {entry_id: mock_coordinator}
    
    # Make async_sync_logs raise an exception
    mock_coordinator.async_sync_logs.side_effect = Exception("Test error")
    
    # Set up the service call
    call = MagicMock()
    call.data = {}
    
    # Capture handler
    handlers = {}
    mock_hass.services.async_register.side_effect = lambda d, s, h, **k: handlers.update({s: h})
    await async_setup_services(mock_hass)
    handler = handlers["sync_logs"]
    
    with patch("custom_components.boks.services.get_coordinator_from_call", return_value=mock_coordinator):
        with pytest.raises(Exception, match="Test error"):
            await handler(call)


async def test_handle_clean_master_codes_success(mock_hass, mock_coordinator):
    """Test handle_clean_master_codes service success."""
    # Set up hass.data with a coordinator
    entry_id = "test_entry_id"
    mock_hass.data[DOMAIN] = {entry_id: mock_coordinator}
    
    # Set up the service call
    call = MagicMock()
    call.data = {"start_index": 0, "range": 5}
    
    # Capture handler
    handlers = {}
    mock_hass.services.async_register.side_effect = lambda d, s, h, **k: handlers.update({s: h})
    await async_setup_services(mock_hass)
    handler = handlers["clean_master_codes"]
    
    with (
        patch("custom_components.boks.services.get_coordinator_from_call", return_value=mock_coordinator),
        patch("custom_components.boks.services.asyncio.sleep", new_callable=AsyncMock)
    ):
        
        await handler(call)
        
        # Verify that the background task was created
        mock_hass.async_create_task.assert_called_once()


async def test_handle_clean_master_codes_already_running(mock_hass, mock_coordinator):
    """Test handle_clean_master_codes service when already running."""
    # Set up hass.data with a coordinator
    entry_id = "test_entry_id"
    mock_hass.data[DOMAIN] = {entry_id: mock_coordinator}
    
    # Set maintenance status to running
    mock_coordinator.maintenance_status = {"running": True}
    
    # Set up the service call
    call = MagicMock()
    call.data = {"start_index": 0, "range": 5}
    
    # Capture handler
    handlers = {}
    mock_hass.services.async_register.side_effect = lambda d, s, h, **k: handlers.update({s: h})
    await async_setup_services(mock_hass)
    handler = handlers["clean_master_codes"]
    
    with patch("custom_components.boks.services.get_coordinator_from_call", return_value=mock_coordinator):
        with pytest.raises(HomeAssistantError) as excinfo:
            await handler(call)
        assert excinfo.value.translation_key == "maintenance_already_running"


async def test_handle_set_configuration_success(mock_hass, mock_coordinator):


    """Test handle_set_configuration service success."""
    
    
    # Set up hass.data with a coordinator
    
    
    entry_id = "test_entry_id"
    
    
    mock_hass.data[DOMAIN] = {entry_id: mock_coordinator}
    
    # Mock the device_info property
    mock_coordinator.device_info = {"sw_version": "4.5.1"}
    
    
    


    # Set up the service call


    call = MagicMock()


    call.data = {"laposte": True}


    


    # Mock set_configuration on ble_device


    mock_coordinator.ble_device.set_configuration = AsyncMock(return_value=True)


    


    # Capture handler


    handlers = {}


    mock_hass.services.async_register.side_effect = lambda d, s, h, **k: handlers.update({s: h})


    await async_setup_services(mock_hass)


    handler = handlers["set_configuration"]


    


    with patch("custom_components.boks.services.get_coordinator_from_call", return_value=mock_coordinator):


        await handler(call)


        


        mock_coordinator.ble_device.connect.assert_called()


        mock_coordinator.ble_device.set_configuration.assert_called_with(BoksConfigType.SCAN_LAPOSTE_NFC_TAGS, True)


        mock_coordinator.ble_device.disconnect.assert_called()








async def test_service_schemas():


    """Test service schemas."""


    # Test SERVICE_ADD_PARCEL_SCHEMA


    valid_data = {"description": "Test parcel"}


    result = SERVICE_ADD_PARCEL_SCHEMA(valid_data)


    assert result == valid_data


    


    # Test SERVICE_ADD_SINGLE_CODE_SCHEMA


    valid_data = {"code": "ABC123"}


    result = SERVICE_ADD_SINGLE_CODE_SCHEMA(valid_data)


    assert result == valid_data


    


    # Test SERVICE_DELETE_SINGLE_CODE_SCHEMA


    valid_data = {"code": "ABC123"}


    result = SERVICE_DELETE_SINGLE_CODE_SCHEMA(valid_data)


    assert result == valid_data


    


    # Test SERVICE_ADD_MASTER_CODE_SCHEMA


    valid_data = {"code": "ABC123", "index": 1}


    result = SERVICE_ADD_MASTER_CODE_SCHEMA(valid_data)


    assert result == valid_data





    # Test SERVICE_SYNC_LOGS_SCHEMA


    valid_data = {}


    result = SERVICE_SYNC_LOGS_SCHEMA(valid_data)


    assert result == valid_data


    


    # Test SERVICE_CLEAN_MASTER_CODES_SCHEMA


    valid_data = {"start_index": 0, "range": 5}


    result = SERVICE_CLEAN_MASTER_CODES_SCHEMA(valid_data)


    assert result == valid_data





    # Test SERVICE_SET_CONFIGURATION_SCHEMA


    valid_data = {"laposte": True}


    result = SERVICE_SET_CONFIGURATION_SCHEMA(valid_data)


    assert result == valid_data

