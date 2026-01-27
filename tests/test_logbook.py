"""Tests for the Boks logbook integration."""
import pytest
from unittest.mock import MagicMock, patch
from homeassistant.core import HomeAssistant, Event
from homeassistant.components.logbook import LOGBOOK_ENTRY_MESSAGE, LOGBOOK_ENTRY_NAME
from homeassistant.const import ATTR_DEVICE_ID
from custom_components.boks.logbook import async_describe_events
from custom_components.boks.const import DOMAIN, EVENT_LOG
from custom_components.boks.coordinator import BoksDataUpdateCoordinator


async def test_async_describe_events(hass: HomeAssistant):
    """Test the async_describe_events function."""
    # Create a mock for the async_describe_event callback
    mock_async_describe_event = MagicMock()
    
    # Call the function
    async_describe_events(hass, mock_async_describe_event)
    
    # Verify that async_describe_event was called with the correct arguments
    mock_async_describe_event.assert_called_once()
    call_args = mock_async_describe_event.call_args[0]
    assert call_args[0] == DOMAIN
    assert call_args[1] == EVENT_LOG
    assert callable(call_args[2])  # The callback function


async def test_async_describe_log_event_with_translation(hass: HomeAssistant):
    """Test the log event description with translation."""
    # Set up mock coordinator in hass.data
    mock_coordinator = MagicMock(spec=BoksDataUpdateCoordinator)
    mock_coordinator.entry = MagicMock()
    mock_coordinator.entry.entry_id = "test_entry"
    mock_coordinator.get_text.side_effect = lambda cat, key, **kwargs: {
        "event.logs.state.door_opened": "Door was opened",
        "event.logs.state.door_closed": "Door was closed"
    }.get(key, key)
    
    hass.data[DOMAIN] = {"test_entry": mock_coordinator}
    
    # Create a mock for the async_describe_event callback
    mock_async_describe_event = MagicMock()
    
    # Call the function to get the callback
    async_describe_events(hass, mock_async_describe_event)
    
    # Get the callback function that was registered
    callback_func = mock_async_describe_event.call_args[0][2]
    
    # Create a mock event
    mock_event = MagicMock()
    mock_event.data = {
        "description": "door_opened",
        "device_id": "test_entry"
    }
    
    # Call the callback function
    result = callback_func(mock_event)
    
    # Verify the result
    assert isinstance(result, dict)
    assert result[LOGBOOK_ENTRY_NAME] == ""
    assert result[LOGBOOK_ENTRY_MESSAGE] == "Door was opened"
    assert result[ATTR_DEVICE_ID] == "test_entry"


async def test_async_describe_log_event_without_translation(hass: HomeAssistant):
    """Test the log event description without translation."""
    # Set up mock coordinator that returns the key part
    mock_coordinator = MagicMock(spec=BoksDataUpdateCoordinator)
    mock_coordinator.entry = MagicMock()
    mock_coordinator.entry.entry_id = "test_entry"
    mock_coordinator.get_text.side_effect = lambda cat, key, **kwargs: key.split(".")[-1]
    
    hass.data[DOMAIN] = {"test_entry": mock_coordinator}
    
    # Create a mock for the async_describe_event callback
    mock_async_describe_event = MagicMock()
    
    # Call the function to get the callback
    async_describe_events(hass, mock_async_describe_event)
    
    # Get the callback function that was registered
    callback_func = mock_async_describe_event.call_args[0][2]
    
    # Create a mock event
    mock_event = MagicMock()
    mock_event.data = {
        "description": "unknown_event",
        "device_id": "test_entry"
    }
    
    # Call the callback function
    result = callback_func(mock_event)
    
    # Verify the result - should return the description key as the message
    assert isinstance(result, dict)
    assert result[LOGBOOK_ENTRY_NAME] == ""
    assert result[LOGBOOK_ENTRY_MESSAGE] == "unknown_event"
    assert result[ATTR_DEVICE_ID] == "test_entry"


async def test_async_describe_log_event_without_device_id(hass: HomeAssistant):
    """Test the log event description without device_id."""
    # Set up mock coordinator
    mock_coordinator = MagicMock(spec=BoksDataUpdateCoordinator)
    mock_coordinator.get_text.side_effect = lambda cat, key, **kwargs: "Door was opened" if "door_opened" in key else key
    
    # Use config_entry_id to match coordinator finding logic in logbook.py
    mock_coordinator.entry = MagicMock()
    mock_coordinator.entry.entry_id = "test_entry"
    
    hass.data[DOMAIN] = {"test_entry": mock_coordinator}
    
    # Create a mock for the async_describe_event callback
    mock_async_describe_event = MagicMock()
    
    # Call the function to get the callback
    async_describe_events(hass, mock_async_describe_event)
    
    # Get the callback function that was registered
    callback_func = mock_async_describe_event.call_args[0][2]
    
    # Create a mock event without device_id
    mock_event = MagicMock()
    mock_event.data = {
        "description": "door_opened"
        # No device_id
    }
    
    # Call the callback function
    result = callback_func(mock_event)
    
    # Verify the result
    assert isinstance(result, dict)
    assert result[LOGBOOK_ENTRY_NAME] == ""
    assert result[LOGBOOK_ENTRY_MESSAGE] == "Door was opened"
    assert result[ATTR_DEVICE_ID] is None