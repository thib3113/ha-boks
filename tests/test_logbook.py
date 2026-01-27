"""Tests for the Boks logbook integration."""
import pytest
from unittest.mock import MagicMock
from homeassistant.core import HomeAssistant
from homeassistant.components.logbook import LOGBOOK_ENTRY_MESSAGE, LOGBOOK_ENTRY_NAME
from homeassistant.const import ATTR_DEVICE_ID
from custom_components.boks.logbook import async_describe_events
from custom_components.boks.const import DOMAIN, EVENT_LOG

async def test_async_describe_events(hass: HomeAssistant):
    """Test the async_describe_events function."""
    mock_async_describe_event = MagicMock()
    async_describe_events(hass, mock_async_describe_event)
    mock_async_describe_event.assert_called_once()
    call_args = mock_async_describe_event.call_args[0]
    assert call_args[0] == DOMAIN
    assert call_args[1] == EVENT_LOG
    assert callable(call_args[2])

async def test_async_describe_log_event(hass: HomeAssistant):
    """Test the log event description pass-through."""
    mock_async_describe_event = MagicMock()
    async_describe_events(hass, mock_async_describe_event)
    callback_func = mock_async_describe_event.call_args[0][2]
    
    mock_event = MagicMock()
    mock_event.data = {
        "description": "Door was opened by Alice",
        "device_id": "test_entry"
    }
    
    result = callback_func(mock_event)
    
    assert isinstance(result, dict)
    assert result[LOGBOOK_ENTRY_NAME] == ""
    assert result[LOGBOOK_ENTRY_MESSAGE] == "Door was opened by Alice"
    assert result[ATTR_DEVICE_ID] == "test_entry"

async def test_async_describe_log_event_no_device_id(hass: HomeAssistant):
    """Test the log event description without device_id."""
    mock_async_describe_event = MagicMock()
    async_describe_events(hass, mock_async_describe_event)
    callback_func = mock_async_describe_event.call_args[0][2]
    
    mock_event = MagicMock()
    mock_event.data = {
        "description": "Something happened"
    }
    
    result = callback_func(mock_event)
    
    assert result[LOGBOOK_ENTRY_MESSAGE] == "Something happened"
    assert result[ATTR_DEVICE_ID] is None
