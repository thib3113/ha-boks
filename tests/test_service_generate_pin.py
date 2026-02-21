"""Tests for the Boks generate_pin_code service."""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from custom_components.boks.const import DOMAIN
from custom_components.boks.coordinator import BoksDataUpdateCoordinator
from custom_components.boks.errors import BoksError
from custom_components.boks.services import async_setup_services
from homeassistant.core import HomeAssistant
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
    """Create a mock coordinator with pin_generator."""
    coordinator = MagicMock(spec=BoksDataUpdateCoordinator)
    coordinator.pin_generator = MagicMock()
    coordinator.pin_generator.generate_pin = MagicMock(return_value="123456")
    return coordinator

async def test_handle_generate_pin_code_success(mock_hass, mock_coordinator):
    """Test handle_generate_pin_code service success."""
    entry_id = "test_entry_id"
    mock_hass.data[DOMAIN] = {entry_id: mock_coordinator}

    call = MagicMock()
    call.data = {"type": "master", "index": 0}

    handlers = {}
    mock_hass.services.async_register.side_effect = lambda d, s, h, **k: handlers.update({s: h})
    await async_setup_services(mock_hass)
    handler = handlers["generate_pin_code"]

    with patch("custom_components.boks.services.get_coordinator_from_call", return_value=mock_coordinator):
        result = await handler(call)
        
        assert result == {"pin": "123456"}
        mock_coordinator.pin_generator.generate_pin.assert_called_with("master", 0)

async def test_handle_generate_pin_code_boks_error(mock_hass, mock_coordinator):
    """Test handle_generate_pin_code with BoksError (e.g. missing key)."""
    entry_id = "test_entry_id"
    mock_hass.data[DOMAIN] = {entry_id: mock_coordinator}
    
    mock_coordinator.pin_generator.generate_pin.side_effect = BoksError("master_key_required")

    call = MagicMock()
    call.data = {"type": "single", "index": 1}

    handlers = {}
    mock_hass.services.async_register.side_effect = lambda d, s, h, **k: handlers.update({s: h})
    await async_setup_services(mock_hass)
    handler = handlers["generate_pin_code"]

    with patch("custom_components.boks.services.get_coordinator_from_call", return_value=mock_coordinator):
        with pytest.raises(HomeAssistantError) as excinfo:
            await handler(call)
        assert excinfo.value.translation_key == "master_key_required"

async def test_handle_generate_pin_code_unexpected_error(mock_hass, mock_coordinator):
    """Test handle_generate_pin_code with unexpected exception."""
    entry_id = "test_entry_id"
    mock_hass.data[DOMAIN] = {entry_id: mock_coordinator}
    
    mock_coordinator.pin_generator.generate_pin.side_effect = Exception("Unexpected")

    call = MagicMock()
    call.data = {"type": "multi", "index": 2}

    handlers = {}
    mock_hass.services.async_register.side_effect = lambda d, s, h, **k: handlers.update({s: h})
    await async_setup_services(mock_hass)
    handler = handlers["generate_pin_code"]

    with patch("custom_components.boks.services.get_coordinator_from_call", return_value=mock_coordinator):
        with pytest.raises(HomeAssistantError) as excinfo:
            await handler(call)
        assert "Unexpected error" in str(excinfo.value)
