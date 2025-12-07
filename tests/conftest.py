"""Fixtures for Boks integration tests."""
import pytest
import sys
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.boks.const import (
    DOMAIN,
    CONF_MASTER_CODE,
    CONF_CONFIG_KEY,
)

# Set event loop policy for Windows - This is not needed in Docker (Linux) but kept for local Windows dev
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# No global pytest_configure for socket enabling, we will mock components instead.

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the test dir."""
    yield

# Mock problematic Home Assistant core components
@pytest.fixture(autouse=True)
def mock_homeassistant_core_components(hass):
    """Mock Home Assistant core components that cause issues."""
    # Mark components as loaded so HA doesn't try to setup them
    for component in ["recorder", "bluetooth", "logbook", "file_upload", "image_upload", "frontend", "http", "onboarding", "usb", "system_log", "auth", "api", "config", "lovelace", "search", "analytics", "diagnostics", "device_automation", "repairs", "websocket_api"]:
        hass.config.components.add(component)
    
    with patch("homeassistant.components.bluetooth.async_setup", return_value=True), \
         patch("homeassistant.components.recorder.async_setup", return_value=True), \
         patch("homeassistant.components.file_upload.async_setup", return_value=True), \
         patch("homeassistant.components.image_upload.async_setup", return_value=True), \
         patch("homeassistant.components.logbook.async_setup", return_value=True):
        yield

@pytest.fixture
def mock_setup_entry():
    """Override async_setup_entry."""
    with patch(
        "custom_components.boks.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry

@pytest.fixture
def mock_boks_ble_device():
    """Mock the BoksBluetoothDevice."""
    with patch(
        "custom_components.boks.coordinator.BoksBluetoothDevice", autospec=True
    ) as mock_ble_class:
        mock_ble = mock_ble_class.return_value
        mock_ble.connect = AsyncMock()
        mock_ble.disconnect = AsyncMock()
        mock_ble.get_battery_level = AsyncMock(return_value=85)
        mock_ble.get_code_counts = AsyncMock(return_value={"master": 1, "single_use": 2})
        mock_ble.get_device_information = AsyncMock(return_value={
            "manufacturer_name": "Boks",
            "model_number": "Boks ONE",
            "software_revision": "4.5.1",
            "hardware_revision": "v2"
        })
        mock_ble.get_logs_count = AsyncMock(return_value=0)
        mock_ble.get_logs = AsyncMock(return_value=[])
        mock_ble.register_status_callback = MagicMock()
        yield mock_ble

@pytest.fixture
def mock_bluetooth(mock_config_entry_data):
    """Mock bluetooth."""
    mock_ble_device_obj = MagicMock()
    mock_ble_device_obj.address = mock_config_entry_data[CONF_ADDRESS]
    mock_ble_device_obj.name = "Boks"
    with patch("homeassistant.components.bluetooth.async_ble_device_from_address", return_value=mock_ble_device_obj) as mock_bt:
        yield mock_bt

@pytest.fixture
def mock_config_entry_data():
    """Return mock config entry data."""
    return {
        CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
        CONF_MASTER_CODE: "12345A",
        CONF_CONFIG_KEY: "00112233"
    }

@pytest.fixture
def mock_config_entry(mock_config_entry_data):
    """Return a mock config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Boks Test", # Use a consistent title for entity_id generation
        data=mock_config_entry_data,
        options={
            "full_refresh_interval": 0.001, # Set a very short interval for throttling tests
            "scan_interval": 0.001
        },
        entry_id="test_entry_id", # Provide a consistent entry_id
        unique_id=mock_config_entry_data[CONF_ADDRESS]
    )
    return entry