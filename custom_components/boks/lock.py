"""Lock platform for Boks."""
from typing import Any
import logging
import asyncio
import traceback
from datetime import datetime

from homeassistant.components import bluetooth
from homeassistant.components.lock import LockEntity, LockEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_MASTER_CODE, TIMEOUT_DOOR_OPEN_MESSAGE
from .coordinator import BoksDataUpdateCoordinator
from .ble import BoksBluetoothDevice
from .ble.const import BoksHistoryEvent, LOG_EVENT_TYPES
from .entity import BoksEntity
from .errors.boks_command_error import BoksCommandError

_LOGGER = logging.getLogger(__name__)

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
                if event_type in (
                    LOG_EVENT_TYPES[BoksHistoryEvent.DOOR_OPENED],
                    LOG_EVENT_TYPES[BoksHistoryEvent.KEY_OPENING],
                ):
                    return False  # Door is open/unlatched, so lock is unlocked
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
        start_time = datetime.now()
        _LOGGER.debug(f"async_open: Entered at {start_time}")
        _LOGGER.debug(f"Call stack: {''.join(traceback.format_stack())}")

        if self._unlock_lock.locked():
            _LOGGER.warning("async_open: Unlock operation already in progress. Ignoring new request.")
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="door_opened_recently",
                translation_placeholders={"seconds": str(TIMEOUT_DOOR_OPEN_MESSAGE)},
            )

        # Use the unlock lock to prevent concurrent unlock requests
        async with self._unlock_lock:
            _LOGGER.debug(f"async_open: Lock acquired at {datetime.now()} (elapsed: {(datetime.now() - start_time).total_seconds():.3f}s)")

            code = kwargs.get("code")
            if code:
                code = code.strip().upper()
            ble_device: BoksBluetoothDevice = self.coordinator.ble_device

            # Always connect to increment reference counter
            # Try with connectable=True first, then connectable=False
            _LOGGER.debug(f"async_open: getting BLE device from address {self._entry.data[CONF_ADDRESS]}")
            device = bluetooth.async_ble_device_from_address(
                self.hass, self._entry.data[CONF_ADDRESS], connectable=True
            )
            if not device:
                _LOGGER.error("async_open: Device not found in cache")
                raise BoksCommandError("device_not_in_cache")
            
            success = False
            try:
                # Wrap the entire connection and operation in a timeout
                async with asyncio.timeout(20):
                    _LOGGER.debug(f"async_open: Connecting to device... (elapsed: {(datetime.now() - start_time).total_seconds():.3f}s)")
                    await ble_device.connect(device)
                    _LOGGER.debug(f"async_open: Connected. (elapsed: {(datetime.now() - start_time).total_seconds():.3f}s)")

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
                    _LOGGER.debug(f"async_open: Sending open_door command with code length {len(code) if code else 0}... (elapsed: {(datetime.now() - start_time).total_seconds():.3f}s)")
                    await ble_device.open_door(code)
                    _LOGGER.debug(f"async_open: open_door returned successfully. (elapsed: {(datetime.now() - start_time).total_seconds():.3f}s)")

                    # Update state immediately
                    self.coordinator.data["door_open"] = True
                    self.async_write_ha_state()

                    success = True

            except TimeoutError:
                _LOGGER.error("async_open: Operation timed out after 20s")
                raise HomeAssistantError("Operation timed out")
            except Exception as e:
                _LOGGER.error(f"async_open: Error during operation: {e}")
                # Re-raise to ensure HA knows about the failure
                raise e

            finally:
                # Always disconnect to release the device
                if ble_device.is_connected:
                    _LOGGER.debug("async_open: Disconnecting in finally block.")
                    try:
                        # Ensure disconnect doesn't hang forever
                        async with asyncio.timeout(5):
                            await asyncio.shield(ble_device.disconnect())
                    except TimeoutError:
                        _LOGGER.warning("async_open: Disconnect timed out")
                    except Exception as e:
                        _LOGGER.error(f"async_open: Error during disconnect: {e}")

            if success:
                # Hold lock for a fixed duration to prevent spamming
                _LOGGER.debug(f"async_open: Waiting {TIMEOUT_DOOR_OPEN_MESSAGE}s (anti-spam) with lock held...")
                await asyncio.sleep(TIMEOUT_DOOR_OPEN_MESSAGE)
                _LOGGER.debug(f"async_open: Anti-spam wait complete. (elapsed: {(datetime.now() - start_time).total_seconds():.3f}s)")

            _LOGGER.debug(f"async_open: Exiting. Success: {success}. Total time: {(datetime.now() - start_time).total_seconds():.3f}s")
