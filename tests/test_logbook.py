"""Tests for the Boks logbook integration."""
from unittest.mock import MagicMock

from homeassistant.components.logbook import LOGBOOK_ENTRY_MESSAGE, LOGBOOK_ENTRY_NAME
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant

from custom_components.boks.const import DOMAIN, EVENT_LOG
from custom_components.boks.logbook import async_describe_events


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
    """Test the log event description."""
    # Create a mock for the async_describe_event callback
    mock_async_describe_event = MagicMock()

    # Call the function to get the callback
    async_describe_events(hass, mock_async_describe_event)

    # Get the callback function that was registered
    callback_func = mock_async_describe_event.call_args[0][2]

    # Create a mock event with a pre-translated description (as the coordinator does)
    mock_event = MagicMock()
    mock_event.data = {
        "description": "Door was opened",
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
    """Test the log event description for unknown event."""
    # Create a mock for the async_describe_event callback
    mock_async_describe_event = MagicMock()

    # Call the function to get the callback
    async_describe_events(hass, mock_async_describe_event)

    # Get the callback function that was registered
    callback_func = mock_async_describe_event.call_args[0][2]

    # Create a mock event with a raw description
    mock_event = MagicMock()
    mock_event.data = {
        "description": "unknown_event",
        "device_id": "test_entry"
    }

    # Call the callback function
    result = callback_func(mock_event)

    # Verify the result
    assert isinstance(result, dict)
    assert result[LOGBOOK_ENTRY_NAME] == ""
    assert result[LOGBOOK_ENTRY_MESSAGE] == "unknown_event"
    assert result[ATTR_DEVICE_ID] == "test_entry"


async def test_async_describe_log_event_without_device_id(hass: HomeAssistant):
    """Test the log event description without device_id."""
    # Create a mock for the async_describe_event callback
    mock_async_describe_event = MagicMock()

    # Call the function to get the callback
    async_describe_events(hass, mock_async_describe_event)

    # Get the callback function that was registered
    callback_func = mock_async_describe_event.call_args[0][2]

    # Create a mock event without device_id
    mock_event = MagicMock()
    mock_event.data = {
        "description": "Door was opened"
        # No device_id
    }

    # Call the callback function
    result = callback_func(mock_event)

    # Verify the result
    assert isinstance(result, dict)
    assert result[LOGBOOK_ENTRY_NAME] == ""
    assert result[LOGBOOK_ENTRY_MESSAGE] == "Door was opened"
    assert result[ATTR_DEVICE_ID] is None
