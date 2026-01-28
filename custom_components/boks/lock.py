"""Lock platform for Boks."""
import asyncio
import logging
from datetime import datetime
from typing import Any

from homeassistant.components import bluetooth
from homeassistant.components.lock import LockEntity, LockEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .ble import BoksBluetoothDevice
from .ble.const import BoksHistoryEvent, LOG_EVENT_TYPES
from .const import DOMAIN, CONF_MASTER_CODE, TIMEOUT_DOOR_OPEN_MESSAGE, TIMEOUT_DOOR_CLOSE
from .coordinator import BoksDataUpdateCoordinator
from .logic.anonymizer import BoksAnonymizer
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
        _LOGGER.debug("async_open: Entered at %s", start_time)

        if self._unlock_lock.locked():
            _LOGGER.warning("async_open: Unlock operation already in progress. Ignoring new request.")
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="door_opened_recently",
                translation_placeholders={"seconds": str(TIMEOUT_DOOR_OPEN_MESSAGE)},
            )

        # Use the unlock lock to prevent concurrent unlock requests
        async with self._unlock_lock:
            _LOGGER.debug("async_open: Lock acquired at %s (elapsed: %.3fs)", datetime.now(), (datetime.now() - start_time).total_seconds())

            code = kwargs.get("code")
            if code:
                code = code.strip().upper()
            ble_device: BoksBluetoothDevice = self.coordinator.ble_device

            # Always connect to increment reference counter
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug("async_open: getting BLE device from address %s", 
                          BoksAnonymizer.anonymize_mac(self._entry.data[CONF_ADDRESS], self.coordinator.ble_device.anonymize_logs))
            
            # Prefer wrapper for logs (contains scanner name)
            scanners = bluetooth.async_scanner_devices_by_address(self.hass, self._entry.data[CONF_ADDRESS], connectable=True)
            device = scanners[0] if scanners else None
            
            if not device:
                device = bluetooth.async_ble_device_from_address(
                    self.hass, self._entry.data[CONF_ADDRESS], connectable=True
                )
            
            if not device:
                _LOGGER.error("async_open: Device not found in cache for %s", 
                              BoksAnonymizer.anonymize_mac(self._entry.data[CONF_ADDRESS], self.coordinator.ble_device.anonymize_logs))
                raise BoksCommandError("device_not_in_cache")

            if _LOGGER.isEnabledFor(logging.DEBUG):
                rssi_now = None
                service_info = bluetooth.async_last_service_info(self.hass, self._entry.data[CONF_ADDRESS], connectable=True)
                if service_info:
                    rssi_now = service_info.rssi
                _LOGGER.debug("async_open: Target scanner identified: %s", 
                              BoksAnonymizer.format_scanner_info(device, self.coordinator.ble_device.anonymize_logs, fallback_rssi=rssi_now))

            success = False
            timeout_open = 40
            try:
                # 1. Operation: Connect and Open
                async with asyncio.timeout(timeout_open):
                    _LOGGER.debug("async_open: Connecting to device... (elapsed: %.3fs)", (datetime.now() - start_time).total_seconds())
                    # Ensure we pass the underlying BLEDevice if it's a wrapper
                    connection_target = getattr(device, "ble_device", device)
                    await ble_device.connect(connection_target)
                    _LOGGER.debug("async_open: Connected. (elapsed: %.3fs)", (datetime.now() - start_time).total_seconds())

                    # Priority: Stored Master Code
                    if not code:
                        code = self._entry.data.get(CONF_MASTER_CODE)
                        if code:
                            _LOGGER.info("Using stored Master Code for opening.")

                    # Fallback: Single-use code
                    if not code and ble_device.config_key_str:
                        for attempt in range(2):
                            try:
                                _LOGGER.debug("Attempting to generate single-use code (Attempt %d)...", attempt + 1)
                                code = await ble_device.create_pin_code(code_type="single")
                                break
                            except Exception as e:
                                _LOGGER.warning("Failed to generate single-use code (Attempt %d): %s", attempt + 1, e)
                                if attempt == 0:
                                    await asyncio.sleep(2)

                    if not code:
                        if not ble_device.config_key_str:
                            raise BoksCommandError("opening_failed_no_code_no_key")
                        raise BoksCommandError("opening_failed_no_code")

                    # Open the door
                    _LOGGER.debug("async_open: Sending open_door command with code length %d...", len(code) if code else 0)
                    await ble_device.open_door(code)

                    # Update state immediately
                    self.coordinator.data["door_open"] = True
                    self.async_write_ha_state()
                    success = True

                # 2. Wait for closure: Stay connected until door is closed
                if success:
                    _LOGGER.info("Door opened. Waiting for close event (max %ds)...", TIMEOUT_DOOR_CLOSE)
                    closed = await ble_device.wait_for_door_closed(timeout=TIMEOUT_DOOR_CLOSE)

                    if not closed:
                        _LOGGER.warning("Door did not close within %ds, sync will happen on disconnect", TIMEOUT_DOOR_CLOSE)
                    else:
                        _LOGGER.debug("Door closed detected. Disconnecting to trigger auto-refresh.")

            except TimeoutError:
                _LOGGER.error("async_open: Operation timed out after %ds", timeout_open)
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key="operation_timed_out",
                    translation_placeholders={"seconds": str(timeout_open)}
                )
            except Exception as e:
                _LOGGER.error("async_open: Error during operation: %s", e)
                raise e

            finally:
                # Always disconnect to release the device
                if ble_device.is_connected:
                    _LOGGER.debug("async_open: Disconnecting in finally block.")
                    try:
                        async with asyncio.timeout(5):
                            await asyncio.shield(ble_device.disconnect())
                    except Exception as e:
                        _LOGGER.error("async_open: Error during disconnect: %s", e)

                # Ensure the lock is held for at least the anti-spam duration
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed < TIMEOUT_DOOR_OPEN_MESSAGE:
                    wait_time = TIMEOUT_DOOR_OPEN_MESSAGE - elapsed
                    _LOGGER.debug("Holding anti-spam lock for additional %.3fs", wait_time)
                    await asyncio.sleep(wait_time)

            _LOGGER.debug("async_open: Exiting. Success: %s. Total time: %.3fs", success, (datetime.now() - start_time).total_seconds())
