"""Test Boks lock functionality."""
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_ADDRESS
from homeassistant.components.lock import LockEntityFeature
from custom_components.boks.const import DOMAIN
from custom_components.boks.lock import MIN_DOOR_OPEN_INTERVAL, BoksLock
from custom_components.boks.coordinator import BoksDataUpdateCoordinator
from custom_components.boks.errors.boks_command_error import BoksCommandError
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_lock_entity_setup(hass: HomeAssistant) -> None:
    """Test that the lock entity is properly set up."""
    # Create a minimal config entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Boks Test",
        data={CONF_ADDRESS: "AA:BB:CC:DD:EE:FF"},
        options={},
        entry_id="test_entry_id",
        unique_id="AA:BB:CC:DD:EE:FF"
    )
    entry.add_to_hass(hass)
    
    # Create a minimal coordinator
    coordinator = BoksDataUpdateCoordinator(hass, entry)
    coordinator.data = {
        "latest_logs": [],
        "door_open": False
    }
    
    # Store coordinator in hass.data
    hass.data[DOMAIN] = {entry.entry_id: coordinator}
    
    # Create the lock entity directly
    lock = BoksLock(coordinator, entry)
    
    # Verify basic properties
    assert lock.unique_id == "AA:BB:CC:DD:EE:FF_lock"
    assert lock.translation_key == "door"
    assert lock.supported_features == LockEntityFeature.OPEN


async def test_lock_is_locked_based_on_logs() -> None:
    """Test that the lock state is determined based on log entries."""
    # Create a minimal config entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Boks Test",
        data={CONF_ADDRESS: "AA:BB:CC:DD:EE:FF"},
        options={},
        entry_id="test_entry_id",
        unique_id="AA:BB:CC:DD:EE:FF"
    )
    
    # Create a minimal coordinator
    coordinator = MagicMock()
    
    # Test when door is open (unlocked) based on logs
    coordinator.data = {
        "latest_logs": [
            {"event_type": "door_opened", "timestamp": 1234567890}
        ],
        "door_open": False  # This should be ignored when logs are present
    }
    
    # Create the lock entity
    lock = BoksLock(coordinator, entry)
    
    # Verify lock state
    assert lock.is_locked is False
    
    # Test when door is closed (locked) based on logs
    coordinator.data = {
        "latest_logs": [
            {"event_type": "door_closed", "timestamp": 1234567895}
        ],
        "door_open": True  # This should be ignored when logs are present
    }
    
    # Verify lock state
    assert lock.is_locked is True


async def test_lock_is_locked_fallback() -> None:
    """Test that the lock state falls back to real-time status when no logs."""
    # Create a minimal config entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Boks Test",
        data={CONF_ADDRESS: "AA:BB:CC:DD:EE:FF"},
        options={},
        entry_id="test_entry_id",
        unique_id="AA:BB:CC:DD:EE:FF"
    )
    
    # Create a minimal coordinator
    coordinator = MagicMock()
    
    # Test when door is open (unlocked) via real-time status
    coordinator.data = {
        "latest_logs": [],  # No logs
        "door_open": True
    }
    
    # Create the lock entity
    lock = BoksLock(coordinator, entry)
    
    # Verify lock state
    assert lock.is_locked is False
    
    # Test when door is closed (locked) via real-time status
    coordinator.data = {
        "latest_logs": [],  # No logs
        "door_open": False
    }
    
    # Verify lock state
    assert lock.is_locked is True


async def test_lock_unlock_calls_open() -> None:
    """Test that unlock method calls the open method."""
    # Create a minimal config entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Boks Test",
        data={CONF_ADDRESS: "AA:BB:CC:DD:EE:FF"},
        options={},
        entry_id="test_entry_id",
        unique_id="AA:BB:CC:DD:EE:FF"
    )
    
    # Create a minimal coordinator
    coordinator = MagicMock()
    coordinator.data = {
        "latest_logs": [],
        "door_open": False
    }
    
    # Create the lock entity
    lock = BoksLock(coordinator, entry)
    
    # Mock the open method
    lock.async_open = AsyncMock()
    
    # Call unlock
    await lock.async_unlock()
    
    # Verify open was called
    lock.async_open.assert_called_once()


async def test_lock_lock_is_noop() -> None:
    """Test that lock method is a no-op (Boks auto-locks)."""
    # Create a minimal config entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Boks Test",
        data={CONF_ADDRESS: "AA:BB:CC:DD:EE:FF"},
        options={},
        entry_id="test_entry_id",
        unique_id="AA:BB:CC:DD:EE:FF"
    )
    
    # Create a minimal coordinator
    coordinator = MagicMock()
    coordinator.data = {
        "latest_logs": [],
        "door_open": False
    }
    
    # Create the lock entity
    lock = BoksLock(coordinator, entry)
    
    # Call lock (should not raise any exception)
    await lock.async_lock()
    
    # If we get here without exception, the test passes


async def test_lock_has_concurrent_prevention_mechanism() -> None:
    """Test that the lock has a concurrent prevention mechanism."""
    # Create a minimal config entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Boks Test",
        data={CONF_ADDRESS: "AA:BB:CC:DD:EE:FF"},
        options={},
        entry_id="test_entry_id",
        unique_id="AA:BB:CC:DD:EE:FF"
    )
    
    # Create a minimal coordinator
    coordinator = MagicMock()
    coordinator.data = {
        "latest_logs": [],
        "door_open": False
    }
    
    # Create the lock entity
    lock = BoksLock(coordinator, entry)
    
    # Verify that the lock has an unlock lock attribute
    assert hasattr(lock, '_unlock_lock')
    assert isinstance(lock._unlock_lock, asyncio.Lock)


async def test_lock_open_rate_limiting() -> None:
    """Test that door opening is rate-limited."""
    # Create a minimal config entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Boks Test",
        data={CONF_ADDRESS: "AA:BB:CC:DD:EE:FF"},
        options={},
        entry_id="test_entry_id",
        unique_id="AA:BB:CC:DD:EE:FF"
    )
    
    # Create a minimal coordinator
    coordinator = MagicMock()
    coordinator.data = {
        "latest_logs": [],
        "door_open": False
    }
    coordinator.ble_device = MagicMock()
    
    # Create the lock entity
    lock = BoksLock(coordinator, entry)
    
    # Mock hass to avoid AttributeError
    lock.hass = MagicMock()
    lock.hass.async_create_task = MagicMock()
    
    # Mock bluetooth device
    with patch("homeassistant.components.bluetooth.async_ble_device_from_address") as mock_bt:
        mock_bt.return_value = MagicMock()
        
        # Mock ble_device methods
        coordinator.ble_device.connect = AsyncMock()
        coordinator.ble_device.disconnect = AsyncMock()
        coordinator.ble_device.open_door = AsyncMock()
        coordinator.ble_device.wait_for_door_closed = AsyncMock(return_value=True)
        
        # Mock _wait_and_disconnect to avoid complex mocking
        lock._wait_and_disconnect = AsyncMock()
        
        # Mock async_write_ha_state to avoid hass dependency
        lock.async_write_ha_state = MagicMock()
        
        # Set a time for the first open (recent)
        now = datetime.now()
        lock._last_open_time = now - (MIN_DOOR_OPEN_INTERVAL - timedelta(seconds=10))
        
        # Second open should fail due to rate limiting
        try:
            await lock.async_open(code="12345A")
            assert False, "Expected BoksCommandError was not raised"
        except BoksCommandError as e:
            # Check the translation key instead of error_code
            assert e.translation_key == "door_opened_recently"
        
        # Advance time beyond the minimum interval
        lock._last_open_time = now - (MIN_DOOR_OPEN_INTERVAL + timedelta(seconds=10))
        
        # Third open should succeed
        await lock.async_open(code="12345A")
        
        # Verify open_door was called once
        coordinator.ble_device.open_door.assert_called_once_with("12345A")