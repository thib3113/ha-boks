"""Tests for the Boks BLE device additional functionality."""

from unittest.mock import AsyncMock, MagicMock, patch, ANY
import pytest
from homeassistant.core import HomeAssistant
from custom_components.boks.ble.const import BoksNotificationOpcode
from custom_components.boks.ble.device import BoksBluetoothDevice
from custom_components.boks.errors import BoksCommandError, BoksError
from custom_components.boks.packets.rx.code_counts import CodeCountsPacket
from custom_components.boks.packets.rx.operation_result import OperationResultPacket
from custom_components.boks.packets.rx.log_count import LogCountPacket

async def test_get_code_counts_success(hass: HomeAssistant):
    """Test get code counts success."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    mock_resp = MagicMock(spec=CodeCountsPacket)
    mock_resp.master_count = 1
    mock_resp.single_use_count = 2

    with patch.object(device, "send_packet", new_callable=AsyncMock, return_value=mock_resp):
        result = await device.get_code_counts()
        assert result["master"] == 1
        assert result["single_use"] == 2

async def test_get_code_counts_timeout(hass: HomeAssistant):
    """Test get code counts timeout."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    with patch.object(device, "send_packet", new_callable=AsyncMock, side_effect=BoksError("timeout_waiting_response")):
        with pytest.raises(BoksError, match="timeout_waiting_response"):
            await device.get_code_counts()

async def test_get_code_counts_invalid_response(hass: HomeAssistant):
    """Test get code counts with invalid response (None or wrong type)."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    # send_packet returns None if nothing matched
    with patch.object(device, "send_packet", new_callable=AsyncMock, return_value=None):
        result = await device.get_code_counts()
        assert result == {}

async def test_create_pin_code_master_success(hass: HomeAssistant):
    """Test create PIN code for master code success."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    mock_resp = MagicMock(spec=OperationResultPacket)
    mock_resp.opcode = BoksNotificationOpcode.CODE_OPERATION_SUCCESS
    
    with patch.object(device, "send_packet", new_callable=AsyncMock, return_value=mock_resp), \
         patch.object(device, "delete_pin_code", new_callable=AsyncMock):
        result = await device.create_pin_code("123456", "master", 0)
        assert result == "123456"

async def test_create_pin_code_single_success(hass: HomeAssistant):
    """Test create PIN code for single use code success."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    mock_resp = MagicMock(spec=OperationResultPacket)
    mock_resp.opcode = BoksNotificationOpcode.CODE_OPERATION_SUCCESS
    
    with patch.object(device, "send_packet", new_callable=AsyncMock, return_value=mock_resp):
        result = await device.create_pin_code("123456", "single")
        assert result == "123456"

async def test_create_pin_code_multi_success(hass: HomeAssistant):
    """Test create PIN code for multi use code success."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    mock_resp = MagicMock(spec=OperationResultPacket)
    mock_resp.opcode = BoksNotificationOpcode.CODE_OPERATION_SUCCESS
    
    with patch.object(device, "send_packet", new_callable=AsyncMock, return_value=mock_resp):
        result = await device.create_pin_code("123456", "multi")
        assert result == "123456"

async def test_create_pin_code_operation_error(hass: HomeAssistant):
    """Test create PIN code with operation error."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    mock_resp = MagicMock(spec=OperationResultPacket)
    mock_resp.opcode = BoksNotificationOpcode.CODE_OPERATION_ERROR
    
    with patch.object(device, "send_packet", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(BoksError, match="create_code_failed"):
            await device.create_pin_code("123456", "single")

async def test_delete_master_code_success(hass: HomeAssistant):
    """Test delete master code success."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    mock_resp = MagicMock(spec=OperationResultPacket)
    mock_resp.opcode = BoksNotificationOpcode.CODE_OPERATION_SUCCESS
    
    with patch.object(device, "send_packet", new_callable=AsyncMock, return_value=mock_resp):
        result = await device.delete_pin_code("master", 0)
        assert result is True

async def test_delete_single_use_code_success(hass: HomeAssistant):
    """Test delete single use code success."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    mock_resp = MagicMock(spec=OperationResultPacket)
    mock_resp.opcode = BoksNotificationOpcode.CODE_OPERATION_SUCCESS
    
    with patch.object(device, "send_packet", new_callable=AsyncMock, return_value=mock_resp):
        result = await device.delete_pin_code("single", "123456")
        assert result is True

async def test_delete_multi_use_code_success(hass: HomeAssistant):
    """Test delete multi use code success."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    mock_resp = MagicMock(spec=OperationResultPacket)
    mock_resp.opcode = BoksNotificationOpcode.CODE_OPERATION_SUCCESS
    
    with patch.object(device, "send_packet", new_callable=AsyncMock, return_value=mock_resp):
        result = await device.delete_pin_code("multi", "123456")
        assert result is True

async def test_delete_pin_code_operation_error(hass: HomeAssistant):
    """Test delete PIN code with operation error."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    mock_resp = MagicMock(spec=OperationResultPacket)
    mock_resp.opcode = BoksNotificationOpcode.CODE_OPERATION_ERROR
    
    with patch.object(device, "send_packet", new_callable=AsyncMock, return_value=mock_resp):
        result = await device.delete_pin_code("single", "123456")
        assert result is False

async def test_get_logs_success(hass: HomeAssistant):
    """Test get logs success."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    # Simulate connected
    device._client = MagicMock()
    device._client.is_connected = True

    # Mock send_packet for request
    with patch.object(device, "send_packet", new_callable=AsyncMock), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        # We need to simulate logs arriving.
        # _get_logs calls send_packet, then waits for event.
        # We can simulate the callback being called.

        async def side_effect_send_packet(*args, **kwargs):
            # Simulate immediate log arrival
            if device._notify_callback:
                # Need to construct a mock packet bytearray for LOG_END_HISTORY
                from custom_components.boks.ble.const import BoksHistoryEvent
                device._notify_callback(BoksHistoryEvent.LOG_END_HISTORY, bytearray())

        device.send_packet.side_effect = side_effect_send_packet

        result = await device.get_logs(2)
        assert isinstance(result, list)
