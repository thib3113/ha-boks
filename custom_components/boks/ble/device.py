"""Bluetooth Low Energy (BLE) communication handling for Boks."""

import asyncio
import logging
import time
import random
from datetime import datetime, timedelta
from typing import Callable, Any, List, Optional, Dict

from bleak import BleakClient
from bleak.exc import BleakError
from bleak.backends.device import BLEDevice
from bleak_retry_connector import establish_connection

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import (
    BoksServiceUUID,
    BoksCommandOpcode,
    BoksNotificationOpcode,
    BoksHistoryEvent,
)
from .log_entry import BoksLogEntry
from ..const import BOKS_CHAR_MAP

_LOGGER = logging.getLogger(__name__)

class BoksError(Exception):
    """Base class for Boks errors."""
    def __init__(self, translation_key: str, translation_placeholders: Dict[str, str] | None = None):
        super().__init__(translation_key) # For generic Exception message if not translated by HA
        self.translation_key = translation_key
        self.translation_placeholders = translation_placeholders or {}

class BoksAuthError(BoksError):
    """Authentication error (Unauthorized)."""

class BoksCommandError(BoksError):
    """Command failed or rejected."""

class BoksBluetoothDevice:
    """Class to handle BLE communication with the Boks."""

    def __init__(self, hass: HomeAssistant, address: str, config_key: str = None):
        """Initialize the Boks BLE client."""
        self.hass = hass
        self.address = address

        # Validate Config Key length: Should be 8 characters.
        # Old installations might have stored master key in config key (e.g., 64 chars),
        # which were previously truncated. Now we enforce the length.
        if config_key and len(config_key) != 8:
            raise BoksAuthError("config_key_invalid_length")

        self._config_key_str = config_key

        _LOGGER.debug("BoksBluetoothDevice initialized with address: %s, Config Key Present: %s",
                       address, bool(config_key))

        self._client: Optional[BleakClient] = None
        self._lock = asyncio.Lock()
        self._response_futures: dict[str, asyncio.Future] = {}
        self._notify_callback = None
        self._status_callback = None
        self._door_status: bool = False
        self._door_event = asyncio.Event()
        self._connection_users = 0
        self._notifications_subscribed = False
        self._response_callbacks: dict[int, Callable[[bytearray], None]] = {}
        self._last_battery_update: Optional[datetime] = None
        self._full_refresh_interval_hours: int = 12  # Default value, will be updated by coordinator

    def register_status_callback(self, callback: Callable[[dict], None]) -> None:
        """Register a callback for status updates."""
        self._status_callback = callback

    def set_full_refresh_interval(self, hours: int) -> None:
        """Set the full refresh interval in hours."""
        self._full_refresh_interval_hours = hours

    def _should_update_battery_info(self) -> bool:
        """Check if battery info should be updated based on the full refresh interval."""
        if self._last_battery_update is None:
            return True
        
        now = datetime.now()
        return (now - self._last_battery_update) >= timedelta(hours=self._full_refresh_interval_hours)

    async def _update_battery_info_after_delay(self) -> None:
        """Update battery information after a short delay to avoid blocking notification handling."""
        try:
            # Small delay to ensure the door closing operation is complete
            await asyncio.sleep(1.0)
            
            # Ensure we have a connection session for this background task
            await self.connect()
            
            update_data = {}

            # Update battery level
            battery_level = await self.get_battery_level()
            if battery_level > 0:
                self._last_battery_update = datetime.now()
                update_data["battery_level"] = battery_level
                _LOGGER.debug("Battery level updated after door closing: %d%%", battery_level)
            
            # Update battery temperature
            battery_temperature = await self.get_battery_temperature()
            if battery_temperature is not None:
                update_data["battery_temperature"] = battery_temperature
                _LOGGER.debug("Battery temperature updated after door closing: %d°C", battery_temperature)
            
            # Propagate updates to coordinator
            if update_data and self._status_callback:
                self._status_callback(update_data)

        except Exception as e:
            _LOGGER.warning("Failed to update battery info after door closing: %s", e)
        finally:
            # Always disconnect to release our reference to the connection
            await self.disconnect()

    @property
    def is_connected(self) -> bool:
        """Return True if connected."""
        return self._client is not None and self._client.is_connected

    async def connect(self, device: BLEDevice = None) -> None:
        """Connect to the Boks."""
        async with self._lock:
            self._connection_users += 1
            _LOGGER.debug("Connect requested. Users: %d, Already connected: %s", self._connection_users, self.is_connected)

            if self.is_connected:
                return

            _LOGGER.debug("Connecting to Boks %s", self.address)

            # Safety check for None device object
            if device is None:
                _LOGGER.warning("BLE device object is None, attempting to fetch from HA bluetooth manager")
                # Try to get the BLEDevice from HA's cache (Best Practice)
                # First try with connectable=True, then with connectable=False
                device = bluetooth.async_ble_device_from_address(
                    self.hass, self.address, connectable=True
                )
                if not device:
                    # If not found with connectable=True, try with connectable=False
                    device = bluetooth.async_ble_device_from_address(
                        self.hass, self.address, connectable=False
                    )

                if device:
                    _LOGGER.debug("Successfully fetched BLE device from HA bluetooth manager")
                else:
                    _LOGGER.warning("Failed to fetch BLE device from HA bluetooth manager, will attempt connection with address only")

            try:
                self._client = await establish_connection(
                    BleakClient,
                    device if device is not None else self.address,
                    self.address,
                )

                if not self._notifications_subscribed:
                    await self._client.start_notify(BoksServiceUUID.NOTIFY_CHARACTERISTIC, self._notification_handler)
                    self._notifications_subscribed = True
                    _LOGGER.info("Subscribed to notifications from Boks %s", self.address)
                else:
                    _LOGGER.debug("Already subscribed to notifications from Boks %s", self.address)
                _LOGGER.info("Connected to Boks %s", self.address)

                # Reset event on connection
                self._door_event.clear()
            except AttributeError as e:
                # Handle specific bleak internal error: 'NoneType' object has no attribute 'details'
                _LOGGER.error("BLE Internal Error during connection: %s", e)
                # If connection fails, decrement the counter
                self._connection_users -= 1
                raise BoksError(f"BLE Internal Error: {e}")
            except Exception:
                # If connection fails, decrement the counter
                self._connection_users -= 1
                raise

    async def disconnect(self) -> None:
        """Disconnect from the Boks."""
        async with self._lock:
            if self._connection_users > 0:
                self._connection_users -= 1

            _LOGGER.debug("Disconnect requested. Users remaining: %d, Will disconnect: %s",
                           self._connection_users, self._connection_users <= 0)

            if self._connection_users > 0:
                _LOGGER.debug("Connection kept active for %d other users", self._connection_users)
                return

            if self._client and self._client.is_connected:
                await self._client.disconnect()
            self._client = None
            self._notifications_subscribed = False
            _LOGGER.info("Disconnected from Boks")

    async def force_disconnect(self) -> None:
        """Force disconnect from the Boks (reset reference counting)."""
        async with self._lock:
            self._connection_users = 0
            if self._client and self._client.is_connected:
                await self._client.disconnect()
            self._client = None
            self._notifications_subscribed = False
            _LOGGER.info("Force disconnected from Boks")

    def _calculate_checksum(self, data: bytearray) -> int:
        """Calculate 8-bit checksum."""
        return sum(data) & 0xFF

    def _build_packet(self, opcode: int, payload: bytes = b"") -> bytearray:
        """Build a command packet."""
        packet = bytearray()
        packet.append(opcode)
        packet.append(len(payload))
        packet.extend(payload)
        packet.append(self._calculate_checksum(packet))
        return packet

    def _check_checksum(self, data: bytearray) -> bool:
        """Verify checksum of received data."""
        if len(data) < 1:
            return False
        payload_part = data[:-1]
        checksum = data[-1]
        return self._calculate_checksum(payload_part) == checksum

    def _log_packet(self, direction: str, data: bytearray):
        """Log packet with sensitive data redacted."""
        if not data:
            return

        opcode = data[0]
        payload = data[2:-1] if len(data) > 3 else b""

        # Redaction logic
        redacted_payload = payload.hex()

        # Opcodes with sensitive payloads
        if opcode == BoksCommandOpcode.OPEN_DOOR:
            redacted_payload = "*** (PIN)"
        elif opcode in (
            BoksCommandOpcode.CREATE_MASTER_CODE,
            BoksCommandOpcode.CREATE_SINGLE_USE_CODE,
            BoksCommandOpcode.CREATE_MULTI_USE_CODE
        ):
            redacted_payload = "*** (Config Key + PIN)"
        elif opcode == BoksCommandOpcode.MASTER_CODE_EDIT:
            redacted_payload = "*** (Config Key + PIN)"
        elif opcode in (
            BoksCommandOpcode.DELETE_MASTER_CODE,
            BoksCommandOpcode.DELETE_SINGLE_USE_CODE,
            BoksCommandOpcode.DELETE_MULTI_USE_CODE
        ):
            redacted_payload = "*** (Config Key)"
        elif opcode == BoksCommandOpcode.SET_CONFIGURATION:
            redacted_payload = "*** (Config Key)"
        elif opcode == BoksCommandOpcode.GENERATE_CODES:
            redacted_payload = "*** (Master Key)"

        _LOGGER.debug("%s Opcode: 0x%02X, Payload: %s, Raw: %s", direction, opcode, redacted_payload, data.hex())

    def _notification_handler(self, sender: int, data: bytearray):
        """Handle incoming notifications."""
        _LOGGER.debug("Raw notification data received: %s", data.hex() if data else "None")
        self._log_packet("RX", data)

        # Log duplicate notifications for debugging
        if hasattr(self, '_last_notification_data') and hasattr(self, '_last_notification_time'):
            current_time = time.time()
            # If same data received within 1 second, log as potential duplicate
            if self._last_notification_data == data and (current_time - self._last_notification_time) < 1.0:
                _LOGGER.debug("Potential duplicate notification received (same data within 1s)")
            self._last_notification_data = data
            self._last_notification_time = current_time
        else:
            self._last_notification_data = data
            self._last_notification_time = time.time()

        if not self._check_checksum(data):
            _LOGGER.error("Invalid checksum in notification: %s", data.hex())
            return

        opcode = data[0]

        if opcode == BoksNotificationOpcode.ERROR_CRC:
            _LOGGER.error("Boks reported CRC error")
        elif opcode == BoksNotificationOpcode.ERROR_UNAUTHORIZED:
            _LOGGER.error("Boks reported Unauthorized access")
        elif opcode == BoksNotificationOpcode.ERROR_BAD_REQUEST:
            _LOGGER.error("Boks reported Bad Request")

        # Handle Door Status Updates
        door_update = False

        if opcode == BoksNotificationOpcode.NOTIFY_DOOR_STATUS or opcode == BoksNotificationOpcode.ANSWER_DOOR_STATUS:
            # Opcode + Len + 2 bytes payload + Checksum = 5 bytes minimum usually, but let's be safe
            if len(data) >= 4:
                # Payload is 2 bytes: [Inverted Status, Live Status]
                # Index 3 is Live Status (0=Closed, 1=Open)
                if len(data) >= 4:
                    raw_state = data[3]
                    self._door_status = (raw_state == 1)
                    door_update = True

        elif opcode == BoksHistoryEvent.DOOR_CLOSED:
            self._door_status = False
            door_update = True

        elif opcode in (BoksHistoryEvent.DOOR_OPENED, BoksHistoryEvent.CODE_KEY_VALID, BoksHistoryEvent.CODE_BLE_VALID, BoksHistoryEvent.NFC_OPENING):
            self._door_status = True
            door_update = True

        if door_update:
            self._door_event.set()
            _LOGGER.debug("Door status update: %s (Opcode: 0x%02X)", "Open" if self._door_status else "Closed", opcode)
            if self._status_callback:
                self._status_callback({"door_open": self._door_status})

            # Check if this is a door closing event and if we should update battery info
            if (not self._door_status and opcode == BoksHistoryEvent.DOOR_CLOSED):
                if self._should_update_battery_info():
                    # Schedule battery info update asynchronously to avoid blocking notification handling
                    self.hass.async_create_task(self._update_battery_info_after_delay())

        # Handle response futures for commands waiting for specific opcodes
        futures_processed = 0
        for key, future in list(self._response_futures.items()):
            if not future.done():
                if str(opcode) in key:
                    _LOGGER.debug("Resolving future for opcode 0x%02X with key '%s'", opcode, key)
                    future.set_result(data)
                    del self._response_futures[key]
                    futures_processed += 1
            else:
                # Future is already done, remove it from tracking
                if key in self._response_futures:
                    del self._response_futures[key]

        if futures_processed > 1:
            _LOGGER.warning("Multiple futures (%d) resolved for opcode 0x%02X - possible duplicate handling", futures_processed, opcode)
        elif futures_processed == 0:
            _LOGGER.debug("No futures waiting for opcode 0x%02X", opcode)

        # Handle response callbacks for specific opcodes
        if opcode in self._response_callbacks:
            try:
                self._response_callbacks[opcode](data)
            except Exception as e:
                _LOGGER.error("Error in callback for opcode 0x%02X: %s", opcode, e)

        if self._notify_callback:
            self._notify_callback(opcode, data)

    async def wait_for_door_closed(self, timeout: float = 180.0) -> bool:
        """
        Wait for the door to be closed.
        Returns True if closed, False if timeout.
        """
        start_time = time.time()

        # If we are not connected, we can't receive notifications
        if not self.is_connected:
             _LOGGER.warning("Cannot wait for door close: Not connected.")
             return False

        _LOGGER.debug("Waiting for door to close (timeout=%ss)", timeout)

        while (time.time() - start_time) < timeout:
            if not self._door_status:
                _LOGGER.debug("Door is closed.")
                return True

            self._door_event.clear()

            remaining = timeout - (time.time() - start_time)
            if remaining <= 0:
                break

            try:
                await asyncio.wait_for(self._door_event.wait(), timeout=remaining)
            except asyncio.TimeoutError:
                break

        _LOGGER.debug("Wait for door close timed out. Status is still Open.")
        return not self._door_status

    async def _send_command(self, opcode: int, payload: bytes = b"", wait_for_opcodes: List[int] = None, timeout: float = 5.0) -> bytearray:
        """Send a command and optionally wait for a specific response."""
        if not self.is_connected:
            await self.connect()

        # Safety check for None client
        if self._client is None:
            raise BoksError("ble_client_none")

        packet = self._build_packet(opcode, payload)

        future = None
        future_key = ""

        if wait_for_opcodes:
            future = asyncio.get_running_loop().create_future()
            future_key = ",".join(map(str, wait_for_opcodes))
            self._response_futures[future_key] = future

        try:
            self._log_packet("TX", packet)
            await self._client.write_gatt_char(BoksServiceUUID.WRITE_CHARACTERISTIC, packet, response=False)

            if future:
                return await asyncio.wait_for(future, timeout=timeout)
            return None

        except asyncio.TimeoutError:
            if future_key in self._response_futures:
                del self._response_futures[future_key]
            raise BoksError("timeout_waiting_response", {"opcode": f"0x{opcode:02X}"})
        except BleakError as e:
            raise BoksError("ble_error", {"error": str(e)})
        except AttributeError as e:
            # Handle specific bleak internal error: 'NoneType' object has no attribute 'details'
            _LOGGER.warning(f"BLE Internal Error during write (forcing disconnect): {e}")
            await self.force_disconnect()
            raise BoksError("ble_internal_error", {"error": str(e)})

    async def get_battery_level(self) -> int:
        """Get battery level."""
        if not self.is_connected:
            await self.connect()

        # Safety check for None client
        if self._client is None:
            _LOGGER.warning("BLE client is None, cannot read battery level")
            return 0

        try:
            payload = await self._client.read_gatt_char(BoksServiceUUID.BATTERY_LEVEL_CHARACTERISTIC)
            if len(payload) == 1:
                return payload[0]
        except Exception as e:
             _LOGGER.warning("Failed to read battery: %s", e)
        return 0

    async def get_battery_temperature(self) -> int | None:
        """Get battery temperature.

        Reads from characteristic 0004 which returns 6 bytes:
        [level_first, level_min, level_mean, level_max, level_last, temperature]
        Temperature is byte 5, converted using formula: value - 25
        """
        if not self.is_connected:
            await self.connect()

        # Safety check for None client
        if self._client is None:
            _LOGGER.warning("BLE client is None, cannot read battery temperature")
            return None

        try:
            # Read from characteristic 0004 using the main service UUID
            # Using bleak's read_gatt_char with UUIDs instead of integer handle
            payload = await self._client.read_gatt_char(BoksServiceUUID.BATTERY_CHARACTERISTIC)
            if len(payload) >= 6:
                # Temperature is the 6th byte (index 5), converted using formula: value - 25
                raw_temp = payload[5]
                
                if raw_temp == 255:
                    _LOGGER.debug("Battery temperature raw value is 255 (Invalid/Unknown).")
                    return None

                temperature = raw_temp - 25
                _LOGGER.debug("Battery temperature raw data: %s, raw_temp: %d, temperature: %d°C", payload.hex(), raw_temp, temperature)
                return temperature
            else:
                _LOGGER.warning("Unexpected payload length for battery temperature: %d bytes", len(payload))
                return None
        except Exception as e:
            _LOGGER.warning("Failed to read battery temperature: %s", e)
            return None

    async def get_internal_firmware_revision(self) -> str | None:
        """Get internal firmware revision (e.g. 10/125)."""
        if not self.is_connected:
            await self.connect()

        # Safety check for None client
        if self._client is None:
            _LOGGER.warning("BLE client is None, cannot read internal firmware revision")
            return None

        try:
            payload = await self._client.read_gatt_char(BoksServiceUUID.INTERNAL_FIRMWARE_REVISION_CHARACTERISTIC)
            return payload.decode("utf-8")
        except Exception as e:
             _LOGGER.warning("Failed to read internal firmware revision: %s", e)
        return None

    async def get_software_revision(self) -> str | None:
        """Get software revision (e.g. 4.2.0)."""
        if not self.is_connected:
            await self.connect()

        # Safety check for None client
        if self._client is None:
            _LOGGER.warning("BLE client is None, cannot read software revision")
            return None

        try:
            payload = await self._client.read_gatt_char(BoksServiceUUID.SOFTWARE_REVISION_CHARACTERISTIC)
            return payload.decode("utf-8")
        except Exception as e:
             _LOGGER.warning("Failed to read software revision: %s", e)
        return None

    async def get_device_information(self) -> dict:
        """Get all device information characteristics."""
        if not self.is_connected:
            await self.connect()

        # Safety check for None client
        if self._client is None:
            _LOGGER.warning("BLE client is None, cannot read device information")
            return {}

        info = {}
        char_map = {
            "system_id": BoksServiceUUID.SYSTEM_ID_CHARACTERISTIC,
            "model_number": BoksServiceUUID.MODEL_NUMBER_CHARACTERISTIC,
            "serial_number": BoksServiceUUID.SERIAL_NUMBER_CHARACTERISTIC,
            "firmware_revision": BoksServiceUUID.INTERNAL_FIRMWARE_REVISION_CHARACTERISTIC,
            "hardware_revision": BoksServiceUUID.HARDWARE_REVISION_CHARACTERISTIC,
            "software_revision": BoksServiceUUID.SOFTWARE_REVISION_CHARACTERISTIC,
            "manufacturer_name": BoksServiceUUID.MANUFACTURER_NAME_CHARACTERISTIC,
        }

        for name, uuid in char_map.items():
            try:
                payload = await self._client.read_gatt_char(uuid)
                # Most are strings, but System ID is bytes usually displayed as hex
                if name == "system_id":
                    info[name] = payload.hex()
                else:
                    info[name] = payload.decode("utf-8")
            except Exception as e:
                _LOGGER.debug("Failed to read %s: %s", name, e)
                info[name] = None

        return info

    async def get_door_status(self) -> bool:
        """Get door status (True=Open)."""
        resp = await self._send_command(
            BoksCommandOpcode.ASK_DOOR_STATUS,
            wait_for_opcodes=[BoksNotificationOpcode.NOTIFY_DOOR_STATUS]
        )
        if resp:
            raw_state = resp[3]
            self._door_status = (raw_state == 1)
            return self._door_status
        return False

    async def open_door(self, pin_code: str) -> bool:
        """Open the door with a PIN code."""
        pin_code = pin_code.strip().upper()

        if len(pin_code) != 6:
            raise BoksError("pin_code_invalid_length")

        payload = pin_code.encode('ascii')
        _LOGGER.warning(f"Sending PIN code: {pin_code}") # Temporary log
        resp = await self._send_command(
            BoksCommandOpcode.OPEN_DOOR,
            payload,
            wait_for_opcodes=[
                BoksNotificationOpcode.VALID_OPEN_CODE,
                BoksNotificationOpcode.INVALID_OPEN_CODE,
                BoksNotificationOpcode.ERROR_UNAUTHORIZED
            ]
        )

        opcode = resp[0]
        if opcode == BoksNotificationOpcode.VALID_OPEN_CODE:
            self._door_status = True
            return True
        elif opcode == BoksNotificationOpcode.INVALID_OPEN_CODE:
            raise BoksCommandError("pin_code_invalid")
        elif opcode == BoksNotificationOpcode.ERROR_UNAUTHORIZED:
            raise BoksAuthError("unauthorized")

        return False

    def _generate_random_pin(self) -> str:
        """Generate a random valid 6-char PIN (0-9, A, B)."""
        return "".join(random.choice(BOKS_CHAR_MAP) for _ in range(6))

    def _validate_pin(self, code: str) -> bool:
        """Validate PIN format."""
        return len(code) == 6 and all(c in BOKS_CHAR_MAP for c in code)

    async def create_pin_code(self, code: str = None, code_type: str = "standard", index: int = 0) -> str:
        """
        Create a PIN code. Returns the created code.
        code_type: 'master', 'single', 'multi'
        """
        _LOGGER.debug("Creating PIN code: code=%s, code_type=%s, index=%d", code, code_type, index)
        if not self._config_key_str:
            _LOGGER.error("Config key required but not present")
            raise BoksAuthError("config_key_required")

        if not code:
            code = self._generate_random_pin()
        else:
            code = code.strip().upper()

        if not self._validate_pin(code):
            raise BoksError("invalid_code_format")

        opcode = 0
        payload = bytearray(self._config_key_str.encode('ascii'))
        payload.extend(code.encode('ascii'))

        if code_type == "master":
            opcode = BoksCommandOpcode.CREATE_MASTER_CODE
            payload.append(index)
        elif code_type == "single":
            opcode = BoksCommandOpcode.CREATE_SINGLE_USE_CODE
        elif code_type == "multi":
            opcode = BoksCommandOpcode.CREATE_MULTI_USE_CODE
        else:
            raise BoksError("unknown_code_type")

        resp = await self._send_command(
            opcode,
            payload,
            wait_for_opcodes=[
                BoksNotificationOpcode.CODE_OPERATION_SUCCESS,
                BoksNotificationOpcode.CODE_OPERATION_ERROR
            ]
        )

        if resp[0] == BoksNotificationOpcode.CODE_OPERATION_SUCCESS:
            _LOGGER.debug("Successfully created PIN code: %s", code)
            return code
        else:
            _LOGGER.error("Failed to create PIN code")
            raise BoksCommandError("create_code_failed")

    async def change_master_code(self, new_code: str, index: int = 0) -> bool:
        """
        Change an existing master code.
        """
        if not self._config_key_str:
            raise BoksAuthError("config_key_required")

        new_code = new_code.strip().upper()

        if not self._validate_pin(new_code):
            raise BoksError("invalid_code_format")

        # Packet: [0x09][Len][ConfigKey(8)][Index(1)][NewCode(6)][Checksum]
        payload = bytearray(self._config_key_str.encode('ascii'))
        payload.append(index)
        payload.extend(new_code.encode('ascii'))

        resp = await self._send_command(
            BoksCommandOpcode.MASTER_CODE_EDIT,
            payload,
            wait_for_opcodes=[
                BoksNotificationOpcode.CODE_OPERATION_SUCCESS,
                BoksNotificationOpcode.CODE_OPERATION_ERROR
            ]
        )

        if resp[0] == BoksNotificationOpcode.CODE_OPERATION_SUCCESS:
            return True
        else:
            raise BoksCommandError("change_master_code_failed")

    async def delete_pin_code(self, code_type: str, index_or_code: Any) -> bool:
        """
        Delete a PIN code.
        """
        if not self._config_key_str:
            raise BoksAuthError("config_key_required")

        opcode = 0
        payload = bytearray(self._config_key_str.encode('ascii'))

        if code_type == "master":
            opcode = BoksCommandOpcode.DELETE_MASTER_CODE
            payload.append(int(index_or_code))
        elif code_type == "single":
            opcode = BoksCommandOpcode.DELETE_SINGLE_USE_CODE
            # For single-use codes, the identifier is the code itself
            if isinstance(index_or_code, str):
                index_or_code = index_or_code.strip().upper()
            payload.extend(str(index_or_code).encode('ascii'))
        elif code_type == "multi":
            opcode = BoksCommandOpcode.DELETE_MULTI_USE_CODE
            # For multi-use codes, the identifier is the code itself
            if isinstance(index_or_code, str):
                index_or_code = index_or_code.strip().upper()
            payload.extend(str(index_or_code).encode('ascii'))
        else:
            raise BoksError("unknown_code_type")

        resp = await self._send_command(
            opcode,
            payload,
            wait_for_opcodes=[
                BoksNotificationOpcode.CODE_OPERATION_SUCCESS,
                BoksNotificationOpcode.CODE_OPERATION_ERROR
            ]
        )
        return resp[0] == BoksNotificationOpcode.CODE_OPERATION_SUCCESS

    async def get_logs(self, count: int = None) -> List[BoksLogEntry]:
        """Fetch logs."""
        async with self._lock: # Ensure exclusive access for log retrieval sequence
            logs = []

            if not self.is_connected:
                # We need to connect. Since we hold the lock, we can't call self.connect() directly
                # if self.connect() also acquires the lock.
                # Looking at connect(), it acquires the lock. Ideally, we should check connection
                # before acquiring lock, OR refactor connect to have an internal version without lock.
                # However, since lock is reentrant only for same task but here we are in async...
                # asyncio.Lock is NOT reentrant.

                # QUICK FIX: Release lock, connect, re-acquire.
                pass

        # REFACTOR STRATEGY:
        # The _send_command method also acquires the lock. Calling _send_command inside a lock block
        # will cause a DEADLOCK.

        # To fix this properly without rewriting everything:
        # 1. We must ensure we are the only one setting _notify_callback.
        # 2. We must NOT hold the lock while calling methods that also acquire the lock (like _send_command).

        # Alternative: Use a separate lock for the callback mechanism, OR simple check.
        if self._notify_callback is not None:
             raise BoksError("Busy: Another operation is already listening for notifications.")

        try:
            # We set the callback. Since we are in async, we are not interrupted until await.
            # But _send_command awaits.

            # 1. Get Count first (this calls _send_command, which locks)
            if count is None:
                count = await self.get_logs_count()
            _LOGGER.debug("Logs count reported by device: %d", count)

            if count == 0:
                _LOGGER.info("No logs to retrieve")
                return logs
        except Exception as e:
            _LOGGER.warning("Failed to get logs count: %s", e)
            return logs

        log_future = asyncio.get_running_loop().create_future()

        def log_callback(opcode, data):
            if opcode == BoksHistoryEvent.LOG_END_HISTORY:
                 if not log_future.done():
                    log_future.set_result(True)
            # Check if opcode is a known history event
            elif opcode in list(BoksHistoryEvent):
                try:
                    payload = data[2:-1] if data and len(data) > 3 else bytearray()
                    _LOGGER.debug("Raw BLE data received - Opcode: 0x%02X, Payload: %s", opcode, payload.hex() if payload else "None")
                    entry = BoksLogEntry.from_raw(opcode, payload)
                    _LOGGER.debug("Parsed log entry result: %s (type: %s)", entry, type(entry))
                    # Additional safety check for None entries
                    if entry is not None:
                        logs.append(entry)
                        _LOGGER.debug("Received log entry: Opcode 0x%02X", opcode)
                    else:
                        _LOGGER.warning("Failed to parse log entry: Opcode 0x%02X", opcode)
                except Exception as e:
                    _LOGGER.error("Error processing log entry: %s", e)
                    _LOGGER.debug("Error details - Opcode: 0x%02X, Data: %s", opcode, data.hex() if data else "None")

        # CRITICAL SECTION START
        # We need to ensure no one else touches _notify_callback while we use it.
        # But we can't hold self._lock because _send_command needs it.
        # We rely on the fact that this is the only method setting _notify_callback for LOGS.
        # Ideally, _send_command shouldn't touch _notify_callback, only _notification_handler reads it.

        self._notify_callback = log_callback

        try:
            _LOGGER.debug("Requesting logs...")
            # Send request with empty payload (length 0)
            # This will acquire _lock, send, and release _lock.
            # Notifications will arrive and trigger _notification_handler -> log_callback
            await self._send_command(BoksCommandOpcode.REQUEST_LOGS, b"")

            # Adjust timeout based on count, minimum 15s
            timeout = max(15.0, count * 1.0)
            await asyncio.wait_for(log_future, timeout=timeout)
            _LOGGER.debug("Finished receiving logs. Total: %d", len(logs))
        except asyncio.TimeoutError:
            _LOGGER.warning("Timed out receiving logs. Received %d logs so far.", len(logs))
        except Exception as e:
            _LOGGER.error("Error during log retrieval: %s", e)
        finally:
            self._notify_callback = None
            # CRITICAL SECTION END

        # Sort logs by timestamp (oldest first), with safety check
        try:
            logs.sort(key=lambda x: getattr(x, "timestamp", 0) if x is not None else 0)
        except Exception as e:
            _LOGGER.warning("Failed to sort logs: %s", e)

        # Filter out any None entries that might have slipped through
        logs = [log for log in logs if log is not None]
        return logs

    async def get_code_counts(self) -> dict:
        """Get count of stored codes."""

        _LOGGER.debug("Call get codes count")
        resp = await self._send_command(
            BoksCommandOpcode.COUNT_CODES,
            wait_for_opcodes=[BoksNotificationOpcode.NOTIFY_CODES_COUNT]
        )
        if resp and len(resp) >= 6:
            payload = resp[2:6]
            master_count =int.from_bytes(payload[0:2], 'big')
            single_use_count =int.from_bytes(payload[2:4], 'big')

            _LOGGER.debug(f"Received counter : master {master_count}; single {single_use_count}")
            return {
                "master": master_count,
                "single_use": single_use_count,
            }
        return {}

    async def get_logs_count(self) -> int:
        """Get the number of logs stored."""
        # Collect all responses for opcode 0x79 (NOTIFY_LOGS_COUNT) for 0.5 seconds
        values = []

        def callback(data):
            if len(data) >= 4:
                # Payload is 2 bytes: [LogCount_MSB][LogCount_LSB] (Big Endian 16-bit integer)
                count = (data[2] << 8) | data[3]
                values.append(count)
                _LOGGER.debug("Received logs count: %d", count)

        # Register the callback
        self._response_callbacks[BoksNotificationOpcode.NOTIFY_LOGS_COUNT] = callback

        try:
            # Send the command
            await self._send_command(BoksCommandOpcode.GET_LOGS_COUNT)

            # Wait for responses
            await asyncio.sleep(0.5)

            # Return the maximum value received, or 0 if none
            result = max(values) if values else 0
            _LOGGER.debug("Final logs count (max of received values): %d", result)
            return result
        finally:
            # Unregister the callback
            self._response_callbacks.pop(BoksNotificationOpcode.NOTIFY_LOGS_COUNT, None)
