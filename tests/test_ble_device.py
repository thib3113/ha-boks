"Tests for the Boks BLE device."
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from homeassistant.core import HomeAssistant
from custom_components.boks.ble.device import BoksBluetoothDevice, BoksError
from custom_components.boks.ble.const import BoksCommandOpcode, BoksNotificationOpcode, BoksServiceUUID

async def test_device_init_valid_key(hass: HomeAssistant):
    """Test initialization with a valid 8-char key."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    assert device._config_key_str == "12345678"

async def test_device_init_no_key(hass: HomeAssistant):
    """Test initialization without a key."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", None)
    assert device._config_key_str is None

async def test_device_init_invalid_key_length_short(hass: HomeAssistant):
    """Test initialization with a key that is too short."""
    with pytest.raises(ValueError, match="Config key must be exactly 8 characters long"):
        BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "1234567")

async def test_device_init_invalid_key_length_long(hass: HomeAssistant):
    """Test initialization with a key that is too long."""
    with pytest.raises(ValueError, match="Config key must be exactly 8 characters long"):
        BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "123456789")

async def test_device_connect_success(hass: HomeAssistant):
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
    
    # Mock internal client state to simulate connection
    mock_client = MagicMock()
    mock_client.is_connected = True
    mock_client.disconnect = AsyncMock()
    device._client = mock_client
    device._connection_users = 1 

    await device.disconnect()
    
    assert device._client is None
    mock_client.disconnect.assert_awaited_once()

# --- New Tests ---

def test_calculate_checksum(hass: HomeAssistant):
    """Test checksum calculation."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    # Simple sum: 1 + 2 + 3 = 6
    data = bytearray([0x01, 0x02, 0x03])
    assert device._calculate_checksum(data) == 0x06
    
    # Overflow: 255 + 1 = 256 -> 0 (modulo 256)
    data = bytearray([0xFF, 0x01])
    assert device._calculate_checksum(data) == 0x00

def test_build_packet(hass: HomeAssistant):
    """Test packet building."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    opcode = 0x10
    payload = b"\x01\x02"
    
    # Expected: [Opcode, Len(2), 0x01, 0x02, Checksum]
    # Checksum: 0x10 + 0x02 + 0x01 + 0x02 = 0x15
    expected = bytearray([0x10, 0x02, 0x01, 0x02, 0x15])
    
    packet = device._build_packet(opcode, payload)
    assert packet == expected

def test_check_checksum(hass: HomeAssistant):
    """Test checksum validation."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    # Valid packet: [0x01, 0x01 (checksum)]
    # Checksum calc: 0x01 = 0x01. Correct.
    assert device._check_checksum(bytearray([0x01, 0x01])) is True
    
    # Invalid packet
    assert device._check_checksum(bytearray([0x01, 0x02])) is False
    
    # Empty packet
    assert device._check_checksum(bytearray()) is False

async def test_notification_handler_door_status(hass: HomeAssistant):
    """Test handling of door status notification."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    # Register a callback
    callback = MagicMock()
    device.register_status_callback(callback)
    
    # Construct a valid notification packet for Door Status Open
    # Opcode: NOTIFY_DOOR_STATUS (0x65 or similar, let's assume 0x65 based on logs/const)
    opcode = BoksNotificationOpcode.NOTIFY_DOOR_STATUS
    # Payload: [Inverted, Live] -> Live=1 means Open.
    payload = b"\x00\x01" 
    # Checksum: Opcode + Len(2) + Payload
    # But the notification handler receives raw data from Bleak which might NOT include Length if structured differently,
    # or Boks sends Opcode + Length + Payload + Checksum.
    # Based on _notification_handler logic:
    # opcode = data[0]
    # if opcode == ...: read data[3]
    # This implies: [Opcode][Len][Byte1][Byte2][Checksum]
    
    # Let's assume protocol is consistent: Opcode, Len, Payload, Checksum
    # Payload b"\x00\x01" len is 2.
    # Packet: [Opcode, 0x02, 0x00, 0x01, Checksum]
    packet = bytearray([opcode, 0x02, 0x00, 0x01])
    checksum = device._calculate_checksum(packet)
    packet.append(checksum)
    
    # Trigger handler
    device._notification_handler(None, packet)
    
    assert device._door_status is True
    callback.assert_called_with({"door_open": True})
    
    # Test Closed
    # Payload: [0x00, 0x00] -> Closed
    packet = bytearray([opcode, 0x02, 0x00, 0x00])
    checksum = device._calculate_checksum(packet)
    packet.append(checksum)
    
    device._notification_handler(None, packet)
    assert device._door_status is False
    callback.assert_called_with({"door_open": False})

async def test_send_command_success(hass: HomeAssistant):
    """Test sending a command successfully."""
    device = BoksBluetoothDevice(hass, "AA:BB:CC:DD:EE:FF", "12345678")
    
    # Mock client
    mock_client = MagicMock()
    mock_client.is_connected = True
    mock_client.write_gatt_char = AsyncMock()
    device._client = mock_client
    device._connection_users = 1
    
    # We need to simulate the response coming back via notification
    # send_command waits for a future.
    
    # Mock _build_packet to return something simple
    with patch.object(device, "_build_packet", return_value=b"\x01\x02\x03") as mock_build:
        # Create a task to simulate the response coming in "later"
        async def simulate_response():
            await asyncio.sleep(0.01)
            # Simulate receiving the response notification
            # We need to trigger the future stored in device._response_futures
            # The key is the expected opcode.
            # Let's say we expect opcode 0x20
            expected_opcode = 0x20
            
            # We need to manually resolve the future because we can't easily inject into _notification_handler 
            # without knowing the future key generation exactly.
            # But _send_command generates the key: str(opcode).
            
            # Actually, let's just use _notification_handler to resolve it properly!
            # We need a valid packet for opcode 0x20.
            packet = bytearray([expected_opcode, 0x00, expected_opcode]) # Simple packet with checksum
            device._notification_handler(None, packet)

        # Run send_command and simulation concurrently
        task = asyncio.create_task(simulate_response())
        
        response = await device._send_command(
            opcode=0x10, 
            payload=b"", 
            wait_for_opcodes=[0x20],
            timeout=1.0
        )
        
        await task
        
        assert response is not None
        assert response[0] == 0x20
        mock_client.write_gatt_char.assert_called_once()
        # Check arguments: char UUID, data, response=False
        args = mock_client.write_gatt_char.call_args
        assert args[0][0] == BoksServiceUUID.WRITE_CHARACTERISTIC
        assert args[0][1] == b"\x01\x02\x03"