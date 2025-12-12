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
from .protocol import BoksProtocol
from ..errors import BoksError, BoksAuthError, BoksCommandError
from ..const import (
    BOKS_CHAR_MAP,
    TIMEOUT_DOOR_CLOSE,
    TIMEOUT_COMMAND_RESPONSE,
    TIMEOUT_LOG_RETRIEVAL_BASE,
    DELAY_BATTERY_UPDATE,
    DELAY_LOG_COUNT_COLLECTION,
    DELAY_RETRY,
    MAX_RETRIES_DEEP_DELETE
)

_LOGGER = logging.getLogger(__name__)

class BoksBluetoothDevice:
    """Class to handle BLE communication with the Boks."""

    def __init__(self, hass: HomeAssistant, address: str, config_key: str = None):
        """Initialize the Boks BLE client."""
        self.hass = hass
        self.address = address

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
        self._opcode_callbacks: dict[int, list[Callable[[bytearray], None]]] = {}
        self._last_battery_update: Optional[datetime] = None
        self._full_refresh_interval_hours: int = 12  # Default value, will be updated by coordinator

    def register_status_callback(self, callback: Callable[[dict], None]) -> None:
        """Register a callback for status updates."""
        self._status_callback = callback

    def set_full_refresh_interval(self, hours: int) -> None:
        """Set the full refresh interval in hours."""
        self._full_refresh_interval_hours = hours

    def register_opcode_callback(self, opcode: int, callback: Callable[[bytearray], None]) -> None:
        """Register a callback for a specific opcode."""
        if opcode not in self._opcode_callbacks:
            self._opcode_callbacks[opcode] = []
        self._opcode_callbacks[opcode].append(callback)

    def unregister_opcode_callback(self, opcode: int, callback: Callable[[bytearray], None]) -> None:
        """Unregister a callback for a specific opcode."""
        if opcode in self._opcode_callbacks:
            try:
                self._opcode_callbacks[opcode].remove(callback)
                # Clean up empty lists
                if not self._opcode_callbacks[opcode]:
                    del self._opcode_callbacks[opcode]
            except ValueError:
                pass  # Callback not found, ignore

    def _should_update_battery_info(self) -> bool:
        """Check if battery info should be updated based on the full refresh interval."""
        if self._last_battery_update is None:
            return True
        now = datetime.now()
        return (now - self._last_battery_update) >= timedelta(hours=self._full_refresh_interval_hours)

    async def _update_battery_info_after_delay(self) -> None:
        """Update battery information after a short delay to avoid blocking notification handling."""
        try:
            await asyncio.sleep(DELAY_BATTERY_UPDATE)

            device = bluetooth.async_ble_device_from_address(
                self.hass, self.address, connectable=True
            )
            if not device:
                device = bluetooth.async_ble_device_from_address(
                    self.hass, self.address, connectable=False
                )

            await self.connect(device=device)

            update_data = {}

            # Update battery level
            battery_level = await self.get_battery_level()
            if battery_level > 0:
                self._last_battery_update = datetime.now()
                update_data["battery_level"] = battery_level
                _LOGGER.debug("Battery level updated after door closing: %d%%", battery_level)

            # Update battery temperature and stats
            battery_stats = await self.get_battery_stats()
            if battery_stats is not None:
                update_data["battery_stats"] = battery_stats
                # Only update battery_temperature if it's present in stats
                if "temperature" in battery_stats and battery_stats["temperature"] is not None:
                    update_data["battery_temperature"] = battery_stats["temperature"]
                _LOGGER.debug("Battery stats updated after door closing: %s", battery_stats)

            if update_data and self._status_callback:
                self._status_callback(update_data)

        except Exception as e:
            _LOGGER.warning("Failed to update battery info after door closing: %s", e)
        finally:
            await self.disconnect()

    @property
    def is_connected(self) -> bool:
        """Return True if connected."""
        return self._client is not None and self._client.is_connected

    async def connect(self, device: BLEDevice = None) -> None:
        """Connect to the Boks."""
        async with self._lock:
            self._connection_users += 1
            if self.is_connected:
                return

            _LOGGER.debug("Connecting to Boks %s", self.address)

            if device is None:
                device = bluetooth.async_ble_device_from_address(
                    self.hass, self.address, connectable=True
                )
                if not device:
                    device = bluetooth.async_ble_device_from_address(
                        self.hass, self.address, connectable=False
                    )

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

                # Reset event on connection
                self._door_event.clear()
            except Exception:
                self._connection_users -= 1
                raise

    async def disconnect(self) -> None:
        """Disconnect from the Boks."""
        async with self._lock:
            if self._connection_users > 0:
                self._connection_users -= 1

            if self._connection_users > 0:
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

    def _log_packet(self, direction: str, data: bytearray):
        """Log packet with sensitive data redacted."""
        if not data:
            return

        opcode = data[0]
        payload = data[2:-1] if len(data) > 3 else b""
        redacted_payload = payload.hex()

        # Opcodes with sensitive payloads
        if opcode == BoksCommandOpcode.OPEN_DOOR:
            redacted_payload = "*** (PIN)"
        elif opcode in (
            BoksCommandOpcode.CREATE_MASTER_CODE,
            BoksCommandOpcode.CREATE_SINGLE_USE_CODE,
            BoksCommandOpcode.CREATE_MULTI_USE_CODE,
            BoksCommandOpcode.MASTER_CODE_EDIT,
            BoksCommandOpcode.DELETE_MASTER_CODE,
            BoksCommandOpcode.DELETE_SINGLE_USE_CODE,
            BoksCommandOpcode.DELETE_MULTI_USE_CODE,
            BoksCommandOpcode.SET_CONFIGURATION,
            BoksCommandOpcode.GENERATE_CODES
        ):
            redacted_payload = "*** (Sensitive)"

        _LOGGER.debug("%s Opcode: 0x%02X, Payload: %s, Raw: %s", direction, opcode, redacted_payload, data.hex())

    def _notification_handler(self, sender: int, data: bytearray):
        """Handle incoming notifications."""
        self._log_packet("RX", data)

        # Log duplicate notifications
        if hasattr(self, '_last_notification_data') and hasattr(self, '_last_notification_time'):
            current_time = time.time()
            if self._last_notification_data == data and (current_time - self._last_notification_time) < 1.0:
                _LOGGER.debug("Potential duplicate notification received")
            self._last_notification_data = data
            self._last_notification_time = current_time
        else:
            self._last_notification_data = data
            self._last_notification_time = time.time()

        if not BoksProtocol.verify_checksum(data):
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
        parsed_status = None

        if opcode == BoksNotificationOpcode.NOTIFY_DOOR_STATUS or opcode == BoksNotificationOpcode.ANSWER_DOOR_STATUS:
            parsed_status = BoksProtocol.parse_door_status(data)
            if parsed_status is not None:
                self._door_status = parsed_status
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

            if not self._door_status and opcode == BoksHistoryEvent.DOOR_CLOSED:
                if self._should_update_battery_info():
                    self.hass.async_create_task(self._update_battery_info_after_delay())

        # Handle response futures
        futures_processed = 0
        for key, future in list(self._response_futures.items()):
            if not future.done():
                if str(opcode) in key:
                    future.set_result(data)
                    del self._response_futures[key]
                    futures_processed += 1
            else:
                if key in self._response_futures:
                    del self._response_futures[key]

        if self._notify_callback:
            self._notify_callback(opcode, data)

        # Handle dedicated callbacks
        if opcode in self._response_callbacks:
            try:
                self._response_callbacks[opcode](data)
            except Exception as e:
                _LOGGER.error("Error in callback for opcode 0x%02X: %s", opcode, e)

        # Handle opcode-specific callbacks
        if opcode in self._opcode_callbacks:
            for callback in self._opcode_callbacks[opcode][:]:  # Create a copy to avoid modification during iteration
                try:
                    callback(data)
                except Exception as e:
                    _LOGGER.error("Error in opcode callback for opcode 0x%02X: %s", opcode, e)

    async def wait_for_door_closed(self, timeout: float = TIMEOUT_DOOR_CLOSE) -> bool:
        """Wait for the door to be closed."""
        start_time = time.time()

        if not self.is_connected:
             _LOGGER.warning("Cannot wait for door close: Not connected.")
             return False

        while (time.time() - start_time) < timeout:
            if not self._door_status:
                return True

            self._door_event.clear()
            remaining = timeout - (time.time() - start_time)
            if remaining <= 0:
                break

            try:
                await asyncio.wait_for(self._door_event.wait(), timeout=remaining)
            except asyncio.TimeoutError:
                break

        return not self._door_status

    async def _send_command(self, opcode: int, payload: bytes = b"", wait_for_opcodes: List[int] = None, timeout: float = TIMEOUT_COMMAND_RESPONSE) -> bytearray:
        """Send a command and optionally wait for a specific response."""
        packet = BoksProtocol.build_packet(opcode, payload)

        # Retry mechanism for connection/write errors
        # We do not retry on TimeoutError (command sent but no reply) to avoid duplication
        max_attempts = 2

        for attempt in range(max_attempts):
            future = None
            future_key = ""

            try:
                if not self.is_connected:
                    await self.connect()

                if self._client is None:
                    raise BoksError("ble_client_none")

                if wait_for_opcodes:
                    future = asyncio.get_running_loop().create_future()
                    future_key = ",".join(map(str, wait_for_opcodes))
                    self._response_futures[future_key] = future

                self._log_packet("TX", packet)
                await self._client.write_gatt_char(BoksServiceUUID.WRITE_CHARACTERISTIC, packet, response=False)

                if future:
                    return await asyncio.wait_for(future, timeout=timeout)
                return None

            except asyncio.TimeoutError:
                # Cleanup future
                if future_key in self._response_futures:
                    del self._response_futures[future_key]
                # Timeout means command was sent but no Ack. We stop here.
                raise BoksError("timeout_waiting_response", {"opcode": f"0x{opcode:02X}"})

            except (BleakError, AttributeError, OSError) as e:
                # Cleanup future before retry
                if future_key in self._response_futures:
                    del self._response_futures[future_key]

                is_last_attempt = (attempt == max_attempts - 1)
                _LOGGER.warning(f"BLE Error during send (Attempt {attempt+1}/{max_attempts}): {e}")

                # Force clean slate
                await self.force_disconnect()

                if is_last_attempt:
                    if isinstance(e, AttributeError):
                         raise BoksError("ble_internal_error", {"error": str(e)})
                    raise BoksError("ble_error", {"error": str(e)})

                # Wait a bit before retrying connection
                await asyncio.sleep(DELAY_RETRY)

        return None

    async def get_battery_level(self) -> int:
        """Get battery level."""
        if not self.is_connected:
            await self.connect()

        if self._client is None:
            return 0

        try:
            payload = await self._client.read_gatt_char(BoksServiceUUID.BATTERY_LEVEL_CHARACTERISTIC)
            if len(payload) == 1:
                return payload[0]
        except Exception as e:
             _LOGGER.warning("Failed to read battery: %s", e)
        return 0

    async def get_battery_stats(self) -> dict | None:
        """Get battery statistics and format."""
        if not self.is_connected:
            await self.connect()

        if self._client is None:
            return None

        # 1. Try Custom Characteristic
        try:
            payload = await self._client.read_gatt_char(BoksServiceUUID.BATTERY_CHARACTERISTIC)
            stats = BoksProtocol.parse_battery_stats(payload)
            if stats:
                _LOGGER.debug(f"Battery stats (Custom): {stats}")
                return stats
            elif payload:
                 _LOGGER.debug("Custom battery char returned invalid data or unknown format.")
        except Exception as e:
            _LOGGER.debug("Custom battery char read failed or unavailable: %s", e)

        # 2. Try Standard Battery Service (2A19)
        try:
            payload = await self._client.read_gatt_char(BoksServiceUUID.BATTERY_LEVEL_CHARACTERISTIC)
            if len(payload) == 1:
                stats = {
                    "format": "measure-single",
                    "level_single": payload[0],
                    "temperature": None
                }
                _LOGGER.debug(f"Battery stats (Standard): {stats}")
                return stats
        except Exception as e:
             _LOGGER.warning("Failed to read standard battery level: %s", e)

        return None

    async def get_battery_temperature(self) -> int | None:
        """Get battery temperature. (Deprecated)"""
        stats = await self.get_battery_stats()
        if stats:
            return stats.get("temperature")
        return None

    async def get_internal_firmware_revision(self) -> str | None:
        """Get internal firmware revision."""
        if not self.is_connected:
            await self.connect()

        if self._client is None:
            return None

        try:
            payload = await self._client.read_gatt_char(BoksServiceUUID.INTERNAL_FIRMWARE_REVISION_CHARACTERISTIC)
            return payload.decode("utf-8")
        except Exception as e:
             _LOGGER.warning("Failed to read internal firmware revision: %s", e)
        return None

    async def get_software_revision(self) -> str | None:
        """Get software revision."""
        if not self.is_connected:
            await self.connect()

        if self._client is None:
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

        if self._client is None:
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
             parsed = BoksProtocol.parse_door_status(resp)
             if parsed is not None:
                 self._door_status = parsed
        return self._door_status

    async def open_door(self, pin_code: str) -> bool:
        """Open the door with a PIN code."""
        pin_code = pin_code.strip().upper()

        if len(pin_code) != 6:
            raise BoksError("pin_code_invalid_length")

        payload = pin_code.encode('ascii')
        _LOGGER.warning(f"Sending PIN code: {pin_code}")
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
        """Generate a random valid 6-char PIN."""
        return "".join(random.choice(BOKS_CHAR_MAP) for _ in range(6))

    def _validate_pin(self, code: str) -> bool:
        """Validate PIN format."""
        return len(code) == 6 and all(c in BOKS_CHAR_MAP for c in code)

    async def create_pin_code(self, code: str = None, type: str = "standard", index: int = 0) -> str:
        """Create a PIN code."""
        if not self._config_key_str:
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

        if type == "master":
            # Clear slot first
            try:
                await self.delete_pin_code(type="master", index_or_code=index)
            except Exception:
                pass

            opcode = BoksCommandOpcode.CREATE_MASTER_CODE
            payload.append(index)
        elif type == "single":
            opcode = BoksCommandOpcode.CREATE_SINGLE_USE_CODE
        elif type == "multi":
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
            return code
        else:
            raise BoksCommandError("create_code_failed")

    async def change_master_code(self, new_code: str, index: int = 0) -> bool:
        """Change an existing master code."""
        if not self._config_key_str:
            raise BoksAuthError("config_key_required")

        new_code = new_code.strip().upper()

        if not self._validate_pin(new_code):
            raise BoksError("invalid_code_format")

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

    async def delete_pin_code(self, type: str, index_or_code: Any) -> bool:
        """Delete a PIN code."""
        if not self._config_key_str:
            raise BoksAuthError("config_key_required")

        opcode = 0
        base_payload = bytearray(self._config_key_str.encode('ascii'))

        if type == "master":
            opcode = BoksCommandOpcode.DELETE_MASTER_CODE
            try:
                index = int(index_or_code)
                if not (0 <= index <= 255):
                    raise ValueError
                payload = base_payload + bytearray([index])
            except (ValueError, TypeError):
                 raise BoksError("invalid_master_code_index")


            success_count = 0
            for _ in range(MAX_RETRIES_DEEP_DELETE):
                resp = await self._send_command(
                    opcode,
                    payload,
                    wait_for_opcodes=[
                        BoksNotificationOpcode.CODE_OPERATION_SUCCESS,
                        BoksNotificationOpcode.CODE_OPERATION_ERROR
                    ]
                )

                if resp[0] == BoksNotificationOpcode.CODE_OPERATION_SUCCESS:
                    success_count += 1
                    await asyncio.sleep(DELAY_RETRY)
                elif resp[0] == BoksNotificationOpcode.CODE_OPERATION_ERROR:
                    break
                else:
                    break

            if success_count > 0:
                return True
            return False

        elif type == "single":
            opcode = BoksCommandOpcode.DELETE_SINGLE_USE_CODE
            if isinstance(index_or_code, str):
                index_or_code = index_or_code.strip().upper()
            payload = base_payload + str(index_or_code).encode('ascii')
        elif type == "multi":
            opcode = BoksCommandOpcode.DELETE_MULTI_USE_CODE
            if isinstance(index_or_code, str):
                index_or_code = index_or_code.strip().upper()
            payload = base_payload + str(index_or_code).encode('ascii')
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
        async with self._lock:
            pass # Acquire check

        if self._notify_callback is not None:
             raise BoksError("Busy: Another operation is already listening for notifications.")

        try:
            if count is None:
                count = await self.get_logs_count()

            if count == 0:
                return []
        except Exception as e:
            _LOGGER.warning("Failed to get logs count: %s", e)
            return []

        log_future = asyncio.get_running_loop().create_future()
        logs = []

        def log_callback(opcode, data):
            if opcode == BoksHistoryEvent.LOG_END_HISTORY:
                 if not log_future.done():
                    log_future.set_result(True)
            elif opcode in list(BoksHistoryEvent):
                entry = BoksProtocol.parse_log_entry(opcode, data)
                if entry:
                    logs.append(entry)

        self._notify_callback = log_callback

        try:
            await self._send_command(BoksCommandOpcode.REQUEST_LOGS, b"")
            timeout = max(TIMEOUT_LOG_RETRIEVAL_BASE, count * 1.0)
            await asyncio.wait_for(log_future, timeout=timeout)
        except asyncio.TimeoutError:
            _LOGGER.warning("Timed out receiving logs.")
        except Exception as e:
            _LOGGER.error("Error during log retrieval: %s", e)
        finally:
            self._notify_callback = None

        logs.sort(key=lambda x: getattr(x, "timestamp", 0) if x is not None else 0)
        return logs

    async def get_code_counts(self) -> dict:
        """Get count of stored codes."""
        resp = await self._send_command(
            BoksCommandOpcode.COUNT_CODES,
            wait_for_opcodes=[BoksNotificationOpcode.NOTIFY_CODES_COUNT]
        )
        # Use Protocol to parse payload
        if resp:
            # Opcode(1) + Len(1) + Payload + Checksum(1)
            # Payload is at index 2
            payload = resp[2:-1]
            return BoksProtocol.parse_code_counts(payload)
        return {}

    async def get_logs_count(self) -> int:
        """Get the number of logs stored."""
        values = []

        def callback(data):
            count = BoksProtocol.parse_logs_count(data)
            if count is not None:
                values.append(count)

        self._response_callbacks[BoksNotificationOpcode.NOTIFY_LOGS_COUNT] = callback

        try:
            await self._send_command(BoksCommandOpcode.GET_LOGS_COUNT)
            await asyncio.sleep(DELAY_LOG_COUNT_COLLECTION)
            result = max(values) if values else 0
            return result
        finally:
            self._response_callbacks.pop(BoksNotificationOpcode.NOTIFY_LOGS_COUNT, None)
