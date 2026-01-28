"""Test the Boks data update coordinator."""
from unittest.mock import MagicMock
from datetime import timedelta
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.boks.coordinator import BoksDataUpdateCoordinator
from custom_components.boks.errors import BoksError


async def test_coordinator_update_success(
    hass: HomeAssistant, 
    mock_boks_ble_device, 
    mock_bluetooth,
    mock_config_entry
) -> None:
    """Test successful data update."""
    coordinator = BoksDataUpdateCoordinator(hass, mock_config_entry)

    await coordinator.async_refresh()
    assert coordinator.data["battery_level"] == 85
    assert coordinator.data["single_use"] == 2
    assert coordinator.data["device_info_service"]["manufacturer_name"] == "Boks"
    
    mock_boks_ble_device.connect.assert_called()
    mock_boks_ble_device.disconnect.assert_called()

async def test_coordinator_update_device_not_found(
    hass: HomeAssistant, 
    mock_boks_ble_device, 
    mock_bluetooth,
    mock_config_entry
) -> None:
    """Test update failure when device is not in cache."""
    coordinator = BoksDataUpdateCoordinator(hass, mock_config_entry)

    # Mock bluetooth device NOT found
    mock_bluetooth["scan"].return_value = []
    mock_bluetooth["addr"].return_value = None
    
    # Mock connect failure
    mock_boks_ble_device.connect.side_effect = BoksError("no_connectable_adapter")

    with pytest.raises(UpdateFailed, match="Error communicating with Boks: no_connectable_adapter"):
        await coordinator._async_update_data()

async def test_coordinator_sync_logs(
    hass: HomeAssistant, 
    mock_boks_ble_device, 
    mock_bluetooth,
    mock_config_entry
) -> None:
    """Test log synchronization."""
    coordinator = BoksDataUpdateCoordinator(hass, mock_config_entry)
    
    # Ensure scanner is found for logs
    mock_bluetooth["scan"].return_value = [mock_bluetooth["wrapper"]]
    
    # Mock logs
    mock_log = MagicMock()
    mock_log.opcode = "open"
    mock_log.payload = b"\x01"
    mock_log.timestamp = 1234567890
    mock_log.event_type = "parcel_delivered"
    mock_log.description = "Parcel Delivered"
    mock_log.extra_data = {}
    
    mock_boks_ble_device.get_logs_count.return_value = 1
    mock_boks_ble_device.get_logs.return_value = [mock_log]
    
    result = await coordinator.async_sync_logs(update_state=True)
    
    assert len(result["latest_logs"]) == 1
    assert result["latest_logs"][0]["event_type"] == "parcel_delivered"
    assert coordinator.data["latest_logs"][0]["event_type"] == "parcel_delivered"

async def test_coordinator_device_info_throttling(
    hass: HomeAssistant, 
    mock_boks_ble_device, 
    mock_bluetooth,
    mock_config_entry,
    freezer
) -> None:
    """Test that device info is throttled."""
    coordinator = BoksDataUpdateCoordinator(hass, mock_config_entry)
    mock_bluetooth["addr"].return_value = MagicMock()

    # First update: should fetch device info
    await coordinator.async_refresh()
    assert mock_boks_ble_device.get_device_information.call_count == 1
    
    # Reset mocks and advance time within the throttling period
    mock_boks_ble_device.get_device_information.reset_mock()
    freezer.tick(timedelta(minutes=1)) # Advance by a short time, less than 12 hours
    
    # Second update: should fetch device info again because time has passed
    await coordinator.async_refresh()
    assert mock_boks_ble_device.get_device_information.call_count == 1

    # Advance time beyond the throttling period
    mock_boks_ble_device.get_device_information.reset_mock()
    freezer.tick(timedelta(hours=mock_config_entry.options["full_refresh_interval"] + 1)) # Advance beyond throttling
    
    # Third update: should fetch device info again
    await coordinator.async_refresh()
    assert mock_boks_ble_device.get_device_information.call_count == 1
