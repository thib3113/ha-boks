"""Tests for the firmware bug workaround in deletion."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from homeassistant.core import HomeAssistant
from custom_components.boks.ble.device import BoksBluetoothDevice
from custom_components.boks.ble.const import BoksNotificationOpcode
from custom_components.boks.packets.rx.operation_result import OperationResultPacket

async def test_delete_pin_code_firmware_bug_workaround(hass: HomeAssistant):
    """Test the workaround for the firmware bug where deletion returns error but succeeds."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    # Mocking get_code_counts to return a count of 1 before, and 0 after
    mock_counts_before = {"master": 1, "single_use": 1}
    mock_counts_after = {"master": 1, "single_use": 0}
    
    # Mock response packet (ERROR)
    mock_error_resp = MagicMock(spec=OperationResultPacket)
    mock_error_resp.opcode = BoksNotificationOpcode.CODE_OPERATION_ERROR

    with patch.object(device, "get_code_counts") as mock_get_counts, \
         patch.object(device, "send_packet", new_callable=AsyncMock) as mock_send:
        
        mock_get_counts.side_effect = [mock_counts_before, mock_counts_after]
        mock_send.return_value = mock_error_resp

        # Deleting a single-use code
        result = await device.delete_pin_code("single", "123456")

        # The result should be True because of the workaround (count decreased)
        assert result is True
        assert mock_get_counts.call_count == 2
        assert mock_send.call_count == 1

async def test_delete_pin_code_real_error(hass: HomeAssistant):
    """Test that if the count does NOT decrease, it still returns False on error."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    mock_counts_before = {"master": 1, "single_use": 1}
    mock_counts_after = {"master": 1, "single_use": 1}
    
    mock_error_resp = MagicMock(spec=OperationResultPacket)
    mock_error_resp.opcode = BoksNotificationOpcode.CODE_OPERATION_ERROR

    with patch.object(device, "get_code_counts") as mock_get_counts, \
         patch.object(device, "send_packet", new_callable=AsyncMock) as mock_send:
        
        mock_get_counts.side_effect = [mock_counts_before, mock_counts_after]
        mock_send.return_value = mock_error_resp

        result = await device.delete_pin_code("single", "123456")

        # Result should be False because count did not decrease
        assert result is False

async def test_delete_master_code_no_workaround(hass: HomeAssistant):
    """Test that master code deletion does not use the workaround."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    mock_error_resp = MagicMock(spec=OperationResultPacket)
    mock_error_resp.opcode = BoksNotificationOpcode.CODE_OPERATION_ERROR

    with patch.object(device, "get_code_counts") as mock_get_counts, \
         patch.object(device, "send_packet", new_callable=AsyncMock) as mock_send:
        
        mock_send.return_value = mock_error_resp

        result = await device.delete_pin_code("master", 0)

        assert result is False
        # get_code_counts should NOT have been called for master code
        assert mock_get_counts.call_count == 0
