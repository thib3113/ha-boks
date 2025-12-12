"""Tests for the Boks BLE device additional functionality."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from homeassistant.core import HomeAssistant
from custom_components.boks.ble.const import BoksNotificationOpcode
from custom_components.boks.ble.device import BoksBluetoothDevice
from custom_components.boks.errors import BoksCommandError, BoksError


async def test_get_code_counts_success(hass: HomeAssistant):
    """Test get code counts success."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    # Mock response from _send_command
    response_packet = bytearray([BoksNotificationOpcode.NOTIFY_CODES_COUNT, 0x03, 0x00, 0x01, 0x00, 0x02, 0x00, 0xC4])
    
    with patch.object(device, "_send_command", new_callable=AsyncMock, return_value=response_packet):
        result = await device.get_code_counts()
        # The function returns a dict, not individual values
        assert result["master"] == 1
        assert result["single_use"] == 2


async def test_get_code_counts_timeout(hass: HomeAssistant):
    """Test get code counts timeout."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    with patch.object(device, "_send_command", new_callable=AsyncMock, side_effect=BoksError("timeout_waiting_response")):
        with pytest.raises(BoksError, match="timeout_waiting_response"):
            await device.get_code_counts()


async def test_get_code_counts_invalid_response(hass: HomeAssistant):
    """Test get code counts with invalid response."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    # Mock invalid response from _send_command
    response_packet = bytearray([BoksNotificationOpcode.NOTIFY_CODES_COUNT, 0x01, 0x00, 0xC3])  # Wrong length
    
    with patch.object(device, "_send_command", new_callable=AsyncMock, return_value=response_packet):
        result = await device.get_code_counts()
        assert result == {}


async def test_create_pin_code_master_success(hass: HomeAssistant):
    """Test create PIN code for master code success."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    # Mock response from _send_command
    response_packet = bytearray([BoksNotificationOpcode.CODE_OPERATION_SUCCESS, 0x00, 0xC0])
    
    with patch.object(device, "_send_command", new_callable=AsyncMock, return_value=response_packet), \
         patch.object(device, "delete_pin_code", new_callable=AsyncMock):
        result = await device.create_pin_code("123456", "master", 0)
        assert result == "123456"


async def test_create_pin_code_single_success(hass: HomeAssistant):
    """Test create PIN code for single use code success."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    # Mock response from _send_command
    response_packet = bytearray([BoksNotificationOpcode.CODE_OPERATION_SUCCESS, 0x00, 0xC0])
    
    with patch.object(device, "_send_command", new_callable=AsyncMock, return_value=response_packet):
        result = await device.create_pin_code("123456", "single")
        assert result == "123456"


async def test_create_pin_code_multi_success(hass: HomeAssistant):
    """Test create PIN code for multi use code success."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    # Mock response from _send_command
    response_packet = bytearray([BoksNotificationOpcode.CODE_OPERATION_SUCCESS, 0x00, 0xC0])
    
    with patch.object(device, "_send_command", new_callable=AsyncMock, return_value=response_packet):
        result = await device.create_pin_code("123456", "multi")
        assert result == "123456"


async def test_create_pin_code_operation_error(hass: HomeAssistant):
    """Test create PIN code with operation error."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    # Mock response from _send_command
    response_packet = bytearray([BoksNotificationOpcode.CODE_OPERATION_ERROR, 0x00, 0xC1])
    
    with patch.object(device, "_send_command", new_callable=AsyncMock, return_value=response_packet):
        with pytest.raises(BoksCommandError, match="create_code_failed"):
            await device.create_pin_code("123456", "single")


async def test_change_master_code_success(hass: HomeAssistant):
    """Test change master code success."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    # Mock response from _send_command
    response_packet = bytearray([BoksNotificationOpcode.CODE_OPERATION_SUCCESS, 0x00, 0xC0])
    
    with patch.object(device, "_send_command", new_callable=AsyncMock, return_value=response_packet):
        result = await device.change_master_code("123456", 0)
        assert result is True


async def test_change_master_code_operation_error(hass: HomeAssistant):
    """Test change master code with operation error."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    # Mock response from _send_command
    response_packet = bytearray([BoksNotificationOpcode.CODE_OPERATION_ERROR, 0x00, 0xC1])
    
    with patch.object(device, "_send_command", new_callable=AsyncMock, return_value=response_packet):
        with pytest.raises(BoksCommandError, match="change_master_code_failed"):
            await device.change_master_code("123456", 0)


async def test_delete_master_code_success(hass: HomeAssistant):
    """Test delete master code success."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    # Mock response from _send_command
    response_packet = bytearray([BoksNotificationOpcode.CODE_OPERATION_SUCCESS, 0x00, 0xC0])
    
    with patch.object(device, "_send_command", new_callable=AsyncMock, return_value=response_packet), \
         patch("asyncio.sleep", new_callable=AsyncMock):  # Mock sleep to avoid delay
        result = await device.delete_pin_code("master", 0)
        assert result is True


async def test_delete_single_use_code_success(hass: HomeAssistant):
    """Test delete single use code success."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    # Mock response from _send_command
    response_packet = bytearray([BoksNotificationOpcode.CODE_OPERATION_SUCCESS, 0x00, 0xC0])
    
    with patch.object(device, "_send_command", new_callable=AsyncMock, return_value=response_packet):
        result = await device.delete_pin_code("single", "123456")
        assert result is True


async def test_delete_multi_use_code_success(hass: HomeAssistant):
    """Test delete multi use code success."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    # Mock response from _send_command
    response_packet = bytearray([BoksNotificationOpcode.CODE_OPERATION_SUCCESS, 0x00, 0xC0])
    
    with patch.object(device, "_send_command", new_callable=AsyncMock, return_value=response_packet):
        result = await device.delete_pin_code("multi", "123456")
        assert result is True


async def test_delete_pin_code_operation_error(hass: HomeAssistant):
    """Test delete PIN code with operation error."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    # Mock response from _send_command
    response_packet = bytearray([BoksNotificationOpcode.CODE_OPERATION_ERROR, 0x00, 0xC1])
    
    with patch.object(device, "_send_command", new_callable=AsyncMock, return_value=response_packet):
        result = await device.delete_pin_code("single", "123456")
        assert result is False


async def test_get_logs_success(hass: HomeAssistant):
    """Test get logs success."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    with patch.object(device, "_send_command", new_callable=AsyncMock), \
         patch("asyncio.sleep", new_callable=AsyncMock):  # Mock sleep to avoid delay
        result = await device.get_logs(2)
        assert isinstance(result, list)


async def test_get_logs_count_callback(hass: HomeAssistant):
    """Test get logs count with callback."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    # Mock response from _send_command
    response_packet = bytearray([0x80, 0x02, 0x00, 0x05, 0x80])  # NOTIFY_LOGS_COUNT with 5 logs
    
    with patch.object(device, "_send_command", new_callable=AsyncMock), \
         patch("asyncio.sleep", new_callable=AsyncMock):  # Mock sleep to avoid delay
        # We can't easily test the callback mechanism, so we'll test the parsing
        from custom_components.boks.ble.protocol import BoksProtocol
        count = BoksProtocol.parse_logs_count(response_packet)
        assert count == 5