"""Test the Boks config flow."""
from unittest.mock import AsyncMock, patch
import pytest

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.core import HomeAssistant

from custom_components.boks.const import DOMAIN, CONF_MASTER_CODE
from homeassistant.const import CONF_ADDRESS, CONF_NAME

async def test_user_flow_valid(hass: HomeAssistant, mock_setup_entry, mock_bluetooth) -> None:
    """Test the user flow with valid data."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
            CONF_MASTER_CODE: "12345A",
        },
    )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Boks DDEEFF"  # Based on logic in config_flow
    assert result2["data"] == {
        CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
        CONF_MASTER_CODE: "12345A",
        CONF_NAME: "Boks DDEEFF",
    }
    assert len(mock_setup_entry.mock_calls) == 1

async def test_user_flow_invalid_master_code(hass: HomeAssistant, mock_bluetooth) -> None:
    """Test the user flow with invalid master code."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
            CONF_MASTER_CODE: "INVALID", # Invalid chars
        },
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {CONF_MASTER_CODE: "invalid_master_code_format"}

async def test_user_flow_invalid_credential(hass: HomeAssistant, mock_bluetooth) -> None:
    """Test the user flow with invalid credential."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
            CONF_MASTER_CODE: "12345A",
            "credential": "INVALID_HEX",
        },
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"credential": "invalid_credential_format"}

async def test_bluetooth_discovery(hass: HomeAssistant, mock_bluetooth) -> None:
    """Test bluetooth discovery."""
    from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
    
    # Mock discovery info
    mock_discovery = AsyncMock(spec=BluetoothServiceInfoBleak)
    mock_discovery.address = "AA:BB:CC:DD:EE:FF"
    mock_discovery.name = "Boks Device"
    mock_discovery.connectable = True

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=mock_discovery,
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    
    # Check if MAC is pre-filled (implied by not asking for it if we were to simulate UI, 
    # but flow logic just stores it in self._discovery_info)
    
    # Continue flow
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
            CONF_MASTER_CODE: "12345A",
        },
    )
    
    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Boks Device"
    assert result2["data"][CONF_ADDRESS] == "AA:BB:CC:DD:EE:FF"
