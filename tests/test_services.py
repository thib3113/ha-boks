"Tests for the Boks services."
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from custom_components.boks.ble.const import BoksConfigType
from custom_components.boks.const import DOMAIN
from custom_components.boks.coordinator import BoksDataUpdateCoordinator
from custom_components.boks.errors import BoksError
from custom_components.boks.services import (
    get_coordinator_from_call,
    async_setup_services,
    SERVICE_ADD_PARCEL_SCHEMA,
    SERVICE_ADD_SINGLE_CODE_SCHEMA,
    SERVICE_DELETE_SINGLE_CODE_SCHEMA,
    SERVICE_ADD_MASTER_CODE_SCHEMA,
    SERVICE_SYNC_LOGS_SCHEMA,
    SERVICE_CLEAN_MASTER_CODES_SCHEMA,
    SERVICE_SET_CONFIGURATION_SCHEMA
)
from custom_components.boks.todo import BoksParcelTodoList
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError


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
    
    # Mock Updates Controller
    coordinator.updates = MagicMock()
    coordinator.updates.ensure_prerequisites = AsyncMock()

    # Mock NFC Controller
    coordinator.nfc = MagicMock()
    coordinator.nfc.start_scan = AsyncMock()
    coordinator.nfc.register_tag = AsyncMock()
    coordinator.nfc.unregister_tag = AsyncMock()

    # Mock Codes Controller
    coordinator.codes = MagicMock()
    coordinator.codes.create_code = AsyncMock(return_value={"code": "ABC123"})
    coordinator.codes.delete_code = AsyncMock(return_value=True)
    coordinator.codes.clean_master_codes = AsyncMock()

    # Mock Parcels Controller
    coordinator.parcels = MagicMock()
    coordinator.parcels.add_parcel = AsyncMock(return_value={"code": "ABC123"})

    # Mock Commands Controller
    coordinator.commands = MagicMock()
    coordinator.commands.open_door = AsyncMock()
    coordinator.commands.sync_logs = AsyncMock()
    coordinator.commands.set_configuration = AsyncMock()
    coordinator.commands.ask_door_status = AsyncMock(return_value={"is_open": True})

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

            # Verify that services were registered (there are 16 services now)
            assert mock_hass.services.async_register.call_count == 16
async def test_handle_nfc_scan_start_success(mock_hass, mock_coordinator):
    """Test handle_nfc_scan_start service success."""
    # Set up hass.data with a coordinator
    entry_id = "test_entry_id"
    mock_hass.data[DOMAIN] = {entry_id: mock_coordinator}

    # Mock coordinator entry
    mock_coordinator.entry = MagicMock()
    mock_coordinator.entry.unique_id = "test_unique_id"
    mock_coordinator.entry.entry_id = entry_id

    # Set up the service call
    call = MagicMock()
    call.data = {}

    # Mock hass bus
    mock_hass.bus = MagicMock()
    mock_hass.bus.async_fire = MagicMock()

    # Mock hass services async_call
    mock_hass.services.async_call = AsyncMock()

    # Mock found UID
    mock_coordinator.ble_device.nfc_scan_start = AsyncMock(return_value="A1B2C3D4")

    # Mock Device Registry
    mock_dr = MagicMock()
    mock_dr.async_get_device.return_value = MagicMock(id="test_device_id")

    # Capture handler
    handlers = {}
    mock_hass.services.async_register.side_effect = lambda d, s, h, **k: handlers.update({s: h})
    await async_setup_services(mock_hass)
    handler = handlers["nfc_scan_start"]

    # Mock async_create_task to capture the coroutine
    captured_tasks = []
    def mock_create_task(coro):
        captured_tasks.append(coro)
        return MagicMock()
    mock_hass.async_create_task = mock_create_task

    with (
        patch("custom_components.boks.services.get_coordinator_from_call", return_value=mock_coordinator),
        patch("homeassistant.helpers.device_registry.async_get", return_value=mock_dr)
    ):
        await handler(call)

        # Await the background task
        if captured_tasks:
            await captured_tasks[0]

        mock_coordinator.nfc.start_scan.assert_called_once()

async def test_handle_nfc_register_tag_success(mock_hass, mock_coordinator):
    """Test handle_nfc_register_tag service success."""
    entry_id = "test_entry_id"
    mock_hass.data[DOMAIN] = {entry_id: mock_coordinator}

    call = MagicMock()
    call.data = {"uid": "A1B2C3D4", "name": "Test Tag"}

    handlers = {}
    mock_hass.services.async_register.side_effect = lambda d, s, h, **k: handlers.update({s: h})
    await async_setup_services(mock_hass)
    handler = handlers["nfc_register_tag"]

    with patch("custom_components.boks.services.get_coordinator_from_call", return_value=mock_coordinator):
        await handler(call)

        mock_coordinator.nfc.register_tag.assert_called_with("A1B2C3D4", "Test Tag")
        mock_coordinator.async_request_refresh.assert_called()

async def test_handle_nfc_unregister_tag_success(mock_hass, mock_coordinator):
    """Test handle_nfc_unregister_tag service success."""
    entry_id = "test_entry_id"
    mock_hass.data[DOMAIN] = {entry_id: mock_coordinator}

    call = MagicMock()
    call.data = {"uid": "A1B2C3D4"}

    handlers = {}
    mock_hass.services.async_register.side_effect = lambda d, s, h, **k: handlers.update({s: h})
    await async_setup_services(mock_hass)
    handler = handlers["nfc_unregister_tag"]

    with patch("custom_components.boks.services.get_coordinator_from_call", return_value=mock_coordinator):
        await handler(call)

        mock_coordinator.nfc.unregister_tag.assert_called_with("A1B2C3D4")
        mock_coordinator.async_request_refresh.assert_called()



async def test_handle_ask_door_status_success(mock_hass, mock_coordinator):
    """Test handle_ask_door_status service success."""
    entry_id = "test_entry_id"
    mock_hass.data[DOMAIN] = {entry_id: mock_coordinator}

    call = MagicMock()
    call.data = {}

    mock_coordinator.ble_device.get_door_status = AsyncMock(return_value=True)

    handlers = {}
    mock_hass.services.async_register.side_effect = lambda d, s, h, **k: handlers.update({s: h})
    await async_setup_services(mock_hass)
    handler = handlers["ask_door_status"]

    with patch("custom_components.boks.services.get_coordinator_from_call", return_value=mock_coordinator):
        await handler(call)

        mock_coordinator.commands.ask_door_status.assert_called_once()


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

    with patch("custom_components.boks.services.get_coordinator_from_call", return_value=mock_coordinator):
        result = await handler(call)

        assert result == {"code": "ABC123"}
        mock_coordinator.parcels.add_parcel.assert_called_once_with(
            description="Test parcel",
            entity_id="test_entity_id",
            device_id=None
        )


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

        with patch("custom_components.boks.services.get_coordinator_from_call", return_value=mock_coordinator):
            await handler(call)

            mock_coordinator.parcels.add_parcel.assert_called_once_with(
                description="Test parcel",
                entity_id=None,
                device_id="test_device_id"
            )


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
        # Capture handler
        handlers = {}
        mock_hass.services.async_register.side_effect = lambda d, s, h, **k: handlers.update({s: h})
        await async_setup_services(mock_hass)
        handler = handlers["add_parcel"]

        with patch("custom_components.boks.services.get_coordinator_from_call", return_value=mock_coordinator):
            await handler(call)

            mock_coordinator.parcels.add_parcel.assert_called_once_with(
                description="Test parcel",
                entity_id=None,
                device_id=None
            )


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
    
    # Mock config entries to allow temporary coordinator creation
    mock_config_entry = MagicMock()
    mock_config_entry.domain = DOMAIN
    mock_hass.config_entries.async_get_entry.return_value = mock_config_entry

    with (
        patch("homeassistant.helpers.entity_registry.async_get", return_value=mock_entity_registry),
        patch("custom_components.boks.services.BoksDataUpdateCoordinator") as mock_coord_cls
    ):
        # Setup mock coordinator instance
        mock_coord_instance = mock_coord_cls.return_value
        mock_coord_instance.parcels.add_parcel.side_effect = HomeAssistantError(translation_domain=DOMAIN, translation_key="todo_entity_not_found")

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
        await handler(call)

        mock_coordinator.codes.create_code.assert_called_with("ABC123", "single")


async def test_handle_add_single_code_boks_error(mock_hass, mock_coordinator):
    """Test handle_add_single_code service error."""
    # Set up hass.data with a coordinator
    entry_id = "test_entry_id"
    mock_hass.data[DOMAIN] = {entry_id: mock_coordinator}

    # Set up the service call
    call = MagicMock()
    call.data = {"code": "ABC123"}

    # Make create_code raise a BoksError
    mock_coordinator.codes.create_code.side_effect = BoksError("test_error")

    # Capture handler
    handlers = {}
    mock_hass.services.async_register.side_effect = lambda d, s, h, **k: handlers.update({s: h})
    await async_setup_services(mock_hass)
    handler = handlers["add_single_code"]

    with patch("custom_components.boks.services.get_coordinator_from_call", return_value=mock_coordinator):
        with pytest.raises(HomeAssistantError) as excinfo:
            await handler(call)
        assert excinfo.value.translation_key == "test_error"


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

        mock_coordinator.codes.delete_code.assert_called_with("single", "ABC123")


async def test_handle_delete_single_code_boks_error(mock_hass, mock_coordinator):
    """Test handle_delete_single_code service error."""
    # Set up hass.data with a coordinator
    entry_id = "test_entry_id"
    mock_hass.data[DOMAIN] = {entry_id: mock_coordinator}

    # Set up the service call
    call = MagicMock()
    call.data = {"code": "ABC123"}

    # Make delete_code raise a BoksError
    mock_coordinator.codes.delete_code.side_effect = BoksError("test_error")

    # Capture handler
    handlers = {}
    mock_hass.services.async_register.side_effect = lambda d, s, h, **k: handlers.update({s: h})
    await async_setup_services(mock_hass)
    handler = handlers["delete_single_code"]

    with patch("custom_components.boks.services.get_coordinator_from_call", return_value=mock_coordinator):
        with pytest.raises(HomeAssistantError) as excinfo:
            await handler(call)
        assert excinfo.value.translation_key == "test_error"


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

        mock_coordinator.commands.sync_logs.assert_called_once()


async def test_handle_sync_logs_exception(mock_hass, mock_coordinator):
    """Test handle_sync_logs service exception."""
    # Set up hass.data with a coordinator
    entry_id = "test_entry_id"
    mock_hass.data[DOMAIN] = {entry_id: mock_coordinator}

    # Set up the service call
    call = MagicMock()
    call.data = {}

    # Make sync_logs raise an exception
    mock_coordinator.commands.sync_logs.side_effect = Exception("Test error")

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
    call.data = {"start_index": 0, "range": 100}

    # Capture handler
    handlers = {}
    mock_hass.services.async_register.side_effect = lambda d, s, h, **k: handlers.update({s: h})
    await async_setup_services(mock_hass)
    handler = handlers["clean_master_codes"]

    with patch("custom_components.boks.services.get_coordinator_from_call", return_value=mock_coordinator):
        await handler(call)
        mock_coordinator.codes.clean_master_codes.assert_called_with(0, 100)


async def test_handle_clean_master_codes_already_running(mock_hass, mock_coordinator):
    """Test handle_clean_master_codes service when already running."""
    # Set up hass.data with a coordinator
    entry_id = "test_entry_id"
    mock_hass.data[DOMAIN] = {entry_id: mock_coordinator}

    # Simulate running status in maintenance_status
    # Wait, clean_master_codes inside controller checks this now.
    # The SERVICE call just delegates. The ERROR is raised by the controller.
    # So we need to mock the controller raising the error.
    
    # Mock clean_master_codes to raise HomeAssistantError
    mock_coordinator.codes.clean_master_codes.side_effect = HomeAssistantError(translation_domain=DOMAIN, translation_key="maintenance_already_running")

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

    # Mock set_configuration on commands controller
    mock_coordinator.commands.set_configuration = AsyncMock()

    # Capture handler
    handlers = {}
    mock_hass.services.async_register.side_effect = lambda d, s, h, **k: handlers.update({s: h})
    await async_setup_services(mock_hass)
    handler = handlers["set_configuration"]

    with patch("custom_components.boks.services.get_coordinator_from_call", return_value=mock_coordinator):
        await handler(call)

        mock_coordinator.commands.set_configuration.assert_called_with(True)


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
