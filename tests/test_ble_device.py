"""Tests for the Boks BLE device."""
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from bleak.exc import BleakError
from homeassistant.core import HomeAssistant
from custom_components.boks.ble.device import BoksBluetoothDevice
from custom_components.boks.errors import BoksError, BoksAuthError
from custom_components.boks.ble.const import BoksNotificationOpcode
from custom_components.boks.packets.base import BoksTXPacket, BoksRXPacket

class MockTXPacket(BoksTXPacket):
    """Mock TX packet for testing."""
    def __init__(self, opcode=0x10, payload=b""):
        super().__init__(opcode)
        self._payload = payload

    def to_bytes(self) -> bytearray:
        """Serialize packet to bytes."""
        return self._build_framed_packet(self._payload)

class MockRXPacket(BoksRXPacket):
    """Mock RX packet for testing."""
    OPCODE = 0x20

async def test_device_init_valid_key(hass: HomeAssistant):
    """Test initialization with a valid 8-char key."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    assert device._config_key_str == "12345678"

async def test_device_init_invalid_key_length(hass: HomeAssistant):
    """Test initialization with invalid key length."""
    with pytest.raises(BoksAuthError, match="config_key_invalid_length"):
        BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "1234567")

async def test_device_connect_success(hass: HomeAssistant, mock_bluetooth):
    """Test successful connection."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")

    with patch("custom_components.boks.ble.device.establish_connection") as mock_establish, \
         patch("custom_components.boks.ble.device.BleakClient") as mock_client_cls:

        mock_client = mock_client_cls.return_value
        mock_client.start_notify = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_establish.return_value = mock_client

        await device.connect()

        assert device.is_connected
        mock_client.start_notify.assert_called()

async def test_device_disconnect(hass: HomeAssistant):
    """Test disconnect."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")

    mock_client = MagicMock()
    mock_client.is_connected = True
    mock_client.disconnect = AsyncMock()
    device._client = mock_client
    device._connection_users = 1

    await device.disconnect()

    assert device._client is None
    mock_client.disconnect.assert_awaited_once()

async def test_send_packet_retry_success(hass: HomeAssistant, mock_bluetooth):
    """Test sending packet with a retry on failure."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")

    mock_client = MagicMock()
    mock_client.is_connected = True
    # First attempt fails with BleakError, second succeeds
    mock_client.write_gatt_char = AsyncMock(side_effect=[BleakError("Write failed"), None])
    mock_client.disconnect = AsyncMock()

    device._client = mock_client
    # Simulate connection established
    with patch.object(device, "connect", new_callable=AsyncMock) as mock_connect, \
         patch.object(device, "force_disconnect", new_callable=AsyncMock) as mock_force_disconnect:

        # We also need to mock force_disconnect to reset client
        mock_force_disconnect.side_effect = lambda: setattr(device, '_client', None)
        # And connect to restore it
        async def side_effect_connect():
            device._client = mock_client
        mock_connect.side_effect = side_effect_connect

        packet = MockTXPacket()
        await device.send_packet(packet, wait_for_opcodes=None)

        # Should have called write twice
        assert mock_client.write_gatt_char.call_count == 2
        # Should have forced disconnect once
        assert mock_force_disconnect.call_count == 1

async def test_send_packet_timeout_no_retry(hass: HomeAssistant, mock_bluetooth):
    """Test that TimeoutError does NOT trigger a retry."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")

    mock_client = MagicMock()
    mock_client.is_connected = True
    mock_client.write_gatt_char = AsyncMock()
    mock_client.disconnect = AsyncMock()
    device._client = mock_client

    # Mock connect
    with patch.object(device, "connect", new_callable=AsyncMock):
        # We expect a timeout waiting for response
        # Using a very short timeout for test speed
        packet = MockTXPacket()
        with pytest.raises(BoksError, match="timeout_waiting_response"):
            await device.send_packet(
                packet,
                wait_for_opcodes=[0x20],
                timeout=0.01
            )

        # Should have called write only ONCE (no retry on timeout logic for response waiting)
        assert mock_client.write_gatt_char.call_count == 1

async def test_notification_handler_door_status(hass: HomeAssistant):
    """Test handling of door status notification."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    callback = MagicMock()
    device.register_status_callback(callback)

    opcode = BoksNotificationOpcode.NOTIFY_DOOR_STATUS
    # [Opcode, Len, Inverted(0), Live(1), Checksum]
    # Checksum: 0x84 + 0x02 + 0x00 + 0x01 = 0x87
    packet_data = bytearray([opcode, 0x02, 0x00, 0x01, 0x87])

    device._notification_handler(None, packet_data)

    assert device._door_status is True
    callback.assert_called_with({"door_open": True})

async def test_set_configuration_success(hass: HomeAssistant):
    """Test successful set_configuration."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")

    # Mock send_packet to return success packet
    mock_resp = MagicMock(spec=BoksRXPacket)
    mock_resp.opcode = BoksNotificationOpcode.NOTIFY_SET_CONFIGURATION_SUCCESS

    with patch.object(device, "send_packet", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = mock_resp

        result = await device.set_configuration(0x01, True)

        assert result is True
        mock_send.assert_called_once()
