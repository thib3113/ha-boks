"""Test Boks diagnostics."""
from unittest.mock import MagicMock, patch
from homeassistant.core import HomeAssistant

from custom_components.boks.diagnostics import async_get_config_entry_diagnostics
from custom_components.boks.const import DOMAIN, CONF_CONFIG_KEY

async def test_diagnostics(hass: HomeAssistant, mock_config_entry, mock_boks_ble_device):
    """Test diagnostics redaction."""
    
    # Setup config entry and mock coordinator
    entry = mock_config_entry
    entry.add_to_hass(hass)
    
    # Mock coordinator data with sensitive info
    mock_coordinator = MagicMock()
    mock_coordinator.data = {
        "battery_level": 85,
        "device_info_service": {
            "serial_number": "SENSITIVE_SERIAL_COORDINATOR",
            "manufacturer_name": "Boks"
        }
    }
    
    # Add coordinator to hass.data
    hass.data[DOMAIN] = {entry.entry_id: mock_coordinator}

    # Mock bluetooth lookup
    with patch("homeassistant.components.bluetooth.async_ble_device_from_address", return_value=MagicMock(address="AA:BB:CC:DD:EE:FF", name="Boks Device")):
        diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    # Verify Redaction
    assert diagnostics["entry"]["data"][CONF_CONFIG_KEY] == "**REDACTED**"
    
    # Verify serial number redaction in the top-level device_info_service
    assert diagnostics["device_info_service"]["serial_number"] == "**REDACTED**"
    
    # Verify serial number redaction within coordinator_data
    assert diagnostics["coordinator_data"]["device_info_service"]["serial_number"] == "**REDACTED**"
