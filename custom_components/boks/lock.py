"""Lock platform for Boks."""
from typing import Any
import logging
import asyncio
from datetime import datetime, timedelta

from homeassistant.components import bluetooth
from homeassistant.components.lock import LockEntity, LockEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_MASTER_CODE, TIMEOUT_DOOR_CLOSE, DELAY_POST_DOOR_CLOSE_SYNC
from .coordinator import BoksDataUpdateCoordinator
from .ble import BoksBluetoothDevice
from .ble.const import BoksHistoryEvent, LOG_EVENT_TYPES
from .entity import BoksEntity
from .errors.boks_command_error import BoksCommandError

_LOGGER = logging.getLogger(__name__)

# Minimum time between door openings (30 seconds)
MIN_DOOR_OPEN_INTERVAL = timedelta(seconds=30)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Boks lock."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BoksLock(coordinator, entry)])

class BoksLock(BoksEntity, LockEntity):
    """Representation of a Boks Lock."""

    _attr_translation_key = "door"
    _attr_supported_features = LockEntityFeature.OPEN

    def __init__(self, coordinator: BoksDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the lock."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.data[CONF_ADDRESS]}_lock"
        # Track the last time the door was opened
        self._last_open_time: datetime | None = None
        # Lock to prevent concurrent unlock requests
        self._unlock_lock = asyncio.Lock()

    @property
    def suggested_object_id(self) -> str | None:
        """Return the suggested object id."""
        return "door"

    @property
    def is_locked(self) -> bool:
        """Return true if the lock is locked."""
        # Boks is a latch, it's technically always "locked" until opened.
        # If door is open, it's 'unlocked'.
        # Determine door state based on the latest relevant log entry
        latest_logs = self.coordinator.data.get("latest_logs", [])
        if latest_logs:
            # Find the most recent door state log entry
            for log_entry in reversed(latest_logs):
                event_type = log_entry.get("event_type")
                if event_type == LOG_EVENT_TYPES[BoksHistoryEvent.DOOR_OPENED]:
                    return False  # Door is open, so lock is unlocked
                elif event_type == LOG_EVENT_TYPES[BoksHistoryEvent.DOOR_CLOSED]:
                    return True   # Door is closed, so lock is locked

        # Fallback to real-time status if no relevant logs found
        return not self.coordinator.data.get("door_open", False)

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the device."""
        # Not supported for Boks, use open()
        await self.async_open(**kwargs)

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the device.

        The Boks device is a latch that automatically locks when the door closes.
        There is no explicit lock command needed, so this method is a no-op.
        """
        # Boks auto-locks when door closes, so no action needed
        _LOGGER.debug("Boks device auto-locks when door closes, no explicit lock command needed")

    async def async_open(self, **kwargs: Any) -> None:
        """Open the door."""
        # Use the unlock lock to prevent concurrent unlock requests
        async with self._unlock_lock:
            # Check if enough time has passed since last opening
            if self._last_open_time is not None:
                time_since_last_open = datetime.now() - self._last_open_time
                if time_since_last_open < MIN_DOOR_OPEN_INTERVAL:
                    remaining_time = MIN_DOOR_OPEN_INTERVAL - time_since_last_open
                    raise BoksCommandError(
                        "door_opened_recently",
                        {"seconds": str(remaining_time.seconds)}
                    )

            code = kwargs.get("code")
            if code:
                code = code.strip().upper()
            ble_device: BoksBluetoothDevice = self.coordinator.ble_device

            # Always connect to increment reference counter
            # Try with connectable=True first, then connectable=False
            device = bluetooth.async_ble_device_from_address(
                self.hass, self._entry.data[CONF_ADDRESS], connectable=True
            )
            if not device:
                raise BoksCommandError("device_not_in_cache")
            await ble_device.connect(device)

            success = False
            try:
                # 1. Priority: Use stored Master Code if available
                if not code:
                    code = self._entry.data.get(CONF_MASTER_CODE)
                    if code:
                        _LOGGER.info("Using stored Master Code for opening.")

                # 2. Fallback: Try to generate a single-use code if no master code and we have the key
                if not code and ble_device.config_key_str:
                    for attempt in range(2): # Try twice
                        try:
                            _LOGGER.debug(f"Attempting to generate single-use code (Attempt {attempt+1})...")
                            code = await ble_device.create_pin_code(code_type="single")
                            _LOGGER.debug("Generated single-use code successfully.")
                            break
                        except Exception as e:
                            _LOGGER.warning(f"Failed to generate single-use code (Attempt {attempt+1}): {e}")
                            if attempt == 0:
                                await asyncio.sleep(2) # Wait a bit before retry

                if not code:
                    # Detailed error message for user
                    if not ble_device.config_key_str:
                        raise BoksCommandError("opening_failed_no_code_no_key")

                    raise BoksCommandError("opening_failed_no_code")

                # 3. Open the door
                await ble_device.open_door(code)

                # Update state immediately
                self.coordinator.data["door_open"] = True
                self.async_write_ha_state()

                # Record the time of successful door opening
                self._last_open_time = datetime.now()

                # Launch background task to wait for close and disconnect
                # We do NOT trigger a refresh here because it would disconnect the device immediately,
                # breaking the wait_for_door_close logic. The refresh will be handled in _wait_and_disconnect.
                self.hass.async_create_task(self._wait_and_disconnect(ble_device))
                success = True

            finally:
                # If we failed to launch the background task (e.g. open_door failed),
                # we must disconnect (decrement reference counter) ourselves.
                if not success:
                    await asyncio.shield(ble_device.disconnect())

    async def _wait_and_disconnect(self, ble_device):
        """Keep connection alive to wait for door close and sync logs."""
        _LOGGER.debug(f"Monitoring door status for up to {TIMEOUT_DOOR_CLOSE}s...")
        try:
            # Wait for door to close (timeout)
            # This blocks until door is closed or timeout
            closed = await ble_device.wait_for_door_closed(timeout=TIMEOUT_DOOR_CLOSE)

            if closed:
                _LOGGER.info("Door closed detected. Initiating log sync...")
                # Small delay to ensure device has finished writing logs
                await asyncio.sleep(DELAY_POST_DOOR_CLOSE_SYNC)
            else:
                _LOGGER.debug(f"Door did not close within {TIMEOUT_DOOR_CLOSE}s.")

            # Perform a full refresh (logs, battery, etc.) and disconnect
            # This replaces the manual async_sync_logs and ensures clean disconnection via coordinator
            await self.coordinator.async_request_refresh()

        except Exception as e:
            _LOGGER.warning(f"Error during post-open monitoring: {e}")
        finally:
            # Ensure disconnection if something failed above or if coordinator didn't disconnect
            if ble_device.is_connected:
                _LOGGER.debug("Disconnecting from Boks (cleanup).")
                await asyncio.shield(ble_device.disconnect())
