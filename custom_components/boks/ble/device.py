"Bluetooth Low Energy (BLE) communication handling for Boks."

import asyncio
import logging
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import (
    BoksHistoryEvent,
    BoksNotificationOpcode,
    BoksServiceUUID,
)
from .protocol import BoksProtocol
from ..const import (
    DELAY_RETRY,
    DOMAIN,
    TIMEOUT_COMMAND_RESPONSE,
    TIMEOUT_DOOR_CLOSE,
    TIMEOUT_LOG_COUNT_STABILIZATION,
)
from ..errors import BoksAuthError, BoksError
from ..logic.anonymizer import BoksAnonymizer
from ..packets.base import BoksRXPacket, BoksTXPacket
from ..packets.factory import PacketFactory
from ..packets.rx.code_ble_valid import CodeBleValidPacket
from ..packets.rx.code_key_valid import CodeKeyValidPacket
from ..packets.rx.door_closed import DoorClosedPacket
from ..packets.rx.door_opened import DoorOpenedPacket
from ..packets.rx.door_status import DoorStatusPacket
from ..packets.rx.error_response import ErrorResponsePacket
from ..packets.rx.key_opening import KeyOpeningPacket
from ..packets.rx.nfc_opening import NfcOpeningPacket
from ..packets.rx.nfc_scan_result import NfcScanResultPacket

_LOGGER = logging.getLogger(__name__)

class BoksBluetoothDevice:
    """Class to handle BLE communication with the Boks."""

    def __init__(self, hass: HomeAssistant, address: str, config_key: str = None, anonymize_logs: bool = False):
        """Initialize the Boks BLE client."""
        self.hass = hass
        self.address = address
        self.anonymize_logs = anonymize_logs

        if config_key and len(config_key) != 8:
            raise BoksAuthError("config_key_invalid_length")

        self._config_key_str = config_key

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("BoksBluetoothDevice initialized with address: %s, Config Key Present: %s",
                           BoksAnonymizer.anonymize_mac(address, anonymize_logs), bool(config_key))

        self._client: BleakClient | None = None
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
        self._last_battery_update: datetime | None = None
        self._full_refresh_interval_hours: int = 12
        self._refresh_needed = False
        self._last_door_close_time: float | None = None
        self._last_door_open_time: float | None = None
        self._last_log_count_value: int | None = None
        self._last_log_count_ts: float = 0.0

    @property
    def config_key_str(self) -> str:
        """Return config key string."""
        return self._config_key_str

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
                if not self._opcode_callbacks[opcode]:
                    del self._opcode_callbacks[opcode]
            except ValueError:
                pass

    def _should_update_battery_info(self) -> bool:
        """Check if battery info should be updated based on the full refresh interval."""
        if self._last_battery_update is None:
            return True
        return (datetime.now() - self._last_battery_update) >= timedelta(hours=self._full_refresh_interval_hours)

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._client is not None and self._client.is_connected

    async def connect(self, device: BLEDevice = None) -> None:
        """Connect to the Boks (with lock)."""
        async with self._lock:
            await self._connect(device)

    async def _connect(self, device: BLEDevice = None) -> None:
        """Internal connect (without lock)."""
        self._connection_users += 1
        _LOGGER.debug("BLE Session Start. Active Sessions: %d", self._connection_users)
        if self.is_connected:
            return

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("Connecting to Boks %s (Subscribed: %s)",
                          BoksAnonymizer.anonymize_mac(self.address, self.anonymize_logs),
                          self._notifications_subscribed)

        if device is None:
            device = await self._find_best_device()

        if device:
             self._update_last_rssi(device)
        else:
             _LOGGER.debug("BLE Device not found in HA cache.")

        try:
            await asyncio.sleep(1.0)
            ble_device_to_connect = getattr(device, "ble_device", device)

            self._client = await establish_connection(BleakClient, ble_device_to_connect, self.address)
            _LOGGER.debug("Physical BLE Connection Established to %s",
                          BoksAnonymizer.anonymize_mac(self.address, self.anonymize_logs))
            await self._ensure_notifications()
        except Exception as e:
            await self._handle_connect_error(device, e)
            raise

    async def _find_best_device(self) -> BLEDevice:
        """Find the best connectable BLE device based on RSSI."""
        devices = bluetooth.async_scanner_devices_by_address(self.hass, self.address, connectable=True)

        if not devices:
            self._report_no_connectable_adapter()
            raise BoksError("no_connectable_adapter")

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("Found %d connectable candidates for %s", len(devices),
                          BoksAnonymizer.anonymize_mac(self.address, self.anonymize_logs))

        best_device = None
        best_rssi = -1000

        for dev in devices:
            rssi = getattr(dev, "rssi", None)
            if rssi is None and hasattr(dev, "advertisement"):
                 rssi = dev.advertisement.rssi

            if _LOGGER.isEnabledFor(logging.DEBUG):
                info = BoksAnonymizer.get_scanner_info(dev)
                scanner_display = BoksAnonymizer.get_scanner_display_name(info, self.anonymize_logs)
                _LOGGER.debug(" - [RSSI: %s] %s", info.get("rssi", "None"), scanner_display)

            if rssi is not None and rssi > best_rssi:
                best_rssi = rssi
                best_device = dev

        return best_device or devices[0]

    def _update_last_rssi(self, device: BLEDevice):
        """Update cached RSSI info for logging/errors."""
        service_info = bluetooth.async_last_service_info(self.hass, self.address, connectable=True)
        rssi_log = service_info.rssi if service_info else None
        self._last_rssi_log = rssi_log or -100

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("BLE Device to use: %s",
                          BoksAnonymizer.format_scanner_info(device, self.anonymize_logs, fallback_rssi=self._last_rssi_log))

    def _report_no_connectable_adapter(self):
        """Log details about available non-connectable scanners."""
        scanners = bluetooth.async_scanner_devices_by_address(self.hass, self.address, connectable=False)
        _LOGGER.warning("No connectable BLE adapter found for %s. Scanners available: %s",
                        BoksAnonymizer.anonymize_mac(self.address, self.anonymize_logs),
                        [d.scanner.name for d in scanners])

    async def _ensure_notifications(self):
        """Subscribe to notifications if not already subscribed."""
        if not self._notifications_subscribed:
            await self._client.start_notify(BoksServiceUUID.NOTIFY_CHARACTERISTIC, self._notification_handler)
            self._notifications_subscribed = True
            _LOGGER.info("Subscribed to notifications from Boks %s",
                         BoksAnonymizer.anonymize_mac(self.address, self.anonymize_logs))

    async def _handle_connect_error(self, device: BLEDevice, error: Exception):
        """Handle connection failure and log details."""
        self._connection_users = max(0, self._connection_users - 1)
        fallback_rssi = getattr(self, "_last_rssi_log", None)
        sc_info = BoksAnonymizer.format_scanner_info(device, self.anonymize_logs, fallback_rssi=fallback_rssi)
        error_msg = BoksAnonymizer.anonymize_log_message(str(error), self.anonymize_logs)

        _LOGGER.error("Failed to connect to Boks %s via %s: %s",
                      BoksAnonymizer.anonymize_mac(self.address, self.anonymize_logs),
                      sc_info, error_msg)

    async def disconnect(self) -> None:
        """Disconnect from the Boks (with lock)."""
        async with self._lock:
            await self._disconnect()

    async def _disconnect(self) -> None:
        """Internal disconnect (without lock)."""
        if self._connection_users > 0:
            self._connection_users -= 1
            _LOGGER.debug("BLE Session End. Active Sessions: %d", self._connection_users)

        if self._connection_users > 0:
            return

        # Perform final refresh if needed (e.g. after door closure or opening)
        if self._refresh_needed and self.is_connected:
            # We want to wait at least 5 seconds after ANY door event before syncing
            # to let the device finish internal flash writes and stabilize battery
            last_event_time = max(self._last_door_close_time or 0, self._last_door_open_time or 0)
            if last_event_time > 0:
                elapsed = time.time() - last_event_time
                MIN_SYNC_DELAY = 5.0
                if elapsed < MIN_SYNC_DELAY:
                    wait_time = MIN_SYNC_DELAY - elapsed
                    _LOGGER.debug("Waiting %.1fs before final refresh (to stabilize device)", wait_time)
                    await asyncio.sleep(wait_time)

            await self._perform_final_refresh()
            self._refresh_needed = False

        if self._client and self._client.is_connected:
            await asyncio.shield(self._client.disconnect())
        self._client = None
        self._notifications_subscribed = False
        _LOGGER.info("Physical BLE Connection Closed (Disconnected from Boks)")

    async def _perform_final_refresh(self) -> None:
        """Perform a final data refresh before disconnecting (expects no lock or internal calls)."""
        _LOGGER.debug("Performing final refresh (battery and logs) before disconnect")
        try:
            update_data = {}

            # 1. Battery info
            update_data.update(await self._get_final_battery_info())

            # 2. Logs
            update_data.update(await self._get_final_logs())

            if update_data and self._status_callback:
                self._status_callback(update_data)
        except Exception as e:
            _LOGGER.warning("Error during final refresh: %s", e)

    async def _get_final_battery_info(self) -> dict:
        """Fetch battery level and stats for final refresh."""
        data = {}
        level = await self._get_battery_level()
        stats = await self._get_battery_stats()

        data["battery_level"] = level
        if stats:
            data["battery_stats"] = stats
            if stats.get("temperature") is not None:
                data["battery_temperature"] = stats["temperature"]
        return data

    async def _get_final_logs(self) -> dict:
        """Fetch new logs for final refresh."""
        data = {}
        log_count = await self._get_logs_count()
        if log_count > 0:
            _LOGGER.info("Final refresh: Found %d new logs, fetching...", log_count)
            logs = await self._get_logs(log_count)
            data["latest_logs_raw"] = logs
        return data

    async def force_disconnect(self) -> None:
        """Force disconnect from the Boks (reset reference counting)."""
        async with self._lock:
            self._connection_users = 0
            _LOGGER.debug("BLE Sessions Force Cleared. Active Sessions: 0")
            self._refresh_needed = False
            # Clear any pending futures
            for future in self._response_futures.values():
                if not future.done():
                    future.cancel()
            self._response_futures.clear()

            if self._client and self._client.is_connected:
                try:
                    async with asyncio.timeout(5):
                        await self._client.disconnect()
                except Exception as e:
                    _LOGGER.debug("Error during force disconnect: %s", e)

            self._client = None
            self._notifications_subscribed = False
            _LOGGER.info("Force disconnected from Boks")

    def _log_packet(self, direction: str, packet: BoksTXPacket | BoksRXPacket):
        """Log TX or RX packet with anonymization."""
        if not _LOGGER.isEnabledFor(logging.DEBUG):
            return
        log_info = packet.to_log_dict(self.anonymize_logs)
        _LOGGER.debug("%s Opcode: 0x%02X (%s), Payload: %s, Raw: %s%s",
                      direction, packet.opcode, packet.get_opcode_name(),
                      log_info["payload"], log_info["raw"], log_info.get("suffix", ""))

    async def _send_packet(self, packet: BoksTXPacket, wait_for_opcodes: list[int] = None, timeout: float = TIMEOUT_COMMAND_RESPONSE) -> BoksRXPacket | None:
        """Internal send packet without lock/connection handling."""
        raw_bytes = packet.to_bytes()

        future = None
        future_key = ""

        if not self._client or not self._client.is_connected:
             raise BoksError("ble_client_not_connected")

        try:
            if wait_for_opcodes:
                future = asyncio.get_running_loop().create_future()
                future_key = ",".join(map(str, wait_for_opcodes))
                self._response_futures[future_key] = future

            self._log_packet("TX", packet)
            await self._client.write_gatt_char(BoksServiceUUID.WRITE_CHARACTERISTIC, raw_bytes, response=False)

            if future:
                resp_data = await asyncio.wait_for(future, timeout=timeout)
                return PacketFactory.from_rx_data(resp_data)
            return None

        except TimeoutError as e:
            if future_key in self._response_futures:
                del self._response_futures[future_key]
            raise BoksError("timeout_waiting_response", {"opcode": f"0x{packet.opcode:02X}"}) from e

        except (BleakError, AttributeError, OSError) as e:
            if future_key in self._response_futures:
                del self._response_futures[future_key]
            if isinstance(e, AttributeError):
                 raise BoksError("ble_internal_error", {"error": str(e)}) from e
            raise BoksError("ble_error", {"error": str(e)}) from e

    async def send_packet(self, packet: BoksTXPacket, wait_for_opcodes: list[int] = None, timeout: float = TIMEOUT_COMMAND_RESPONSE) -> BoksRXPacket | None:
        """Send a packet object and optionally wait for a specific response packet (Public)."""
        max_attempts = 2

        for attempt in range(max_attempts):
            try:
                async with self._lock:
                    await self._connect()
                    try:
                        return await self._send_packet(packet, wait_for_opcodes, timeout)
                    finally:
                        await self._disconnect()

            except BoksError as e:
                # If we are disconnected or there is an error, force disconnect and retry
                await self.force_disconnect()

                is_last_attempt = (attempt == max_attempts - 1)
                error_msg = BoksAnonymizer.anonymize_log_message(str(e), self.anonymize_logs)
                _LOGGER.warning("BoksError during send (Attempt %d/%d): %s", attempt + 1, max_attempts, error_msg)

                if is_last_attempt:
                    raise e

                import random
                await asyncio.sleep(DELAY_RETRY + random.uniform(0, 1.0))

            except Exception as e:
                await self.force_disconnect()
                is_last_attempt = (attempt == max_attempts - 1)
                error_msg = BoksAnonymizer.anonymize_log_message(str(e), self.anonymize_logs)
                _LOGGER.warning("Unexpected error during send (Attempt %d/%d): %s", attempt + 1, max_attempts, error_msg)

                if is_last_attempt:
                    raise e

                import random
                await asyncio.sleep(DELAY_RETRY + random.uniform(0, 1.0))

        return None

    def _notification_handler(self, _sender: int, data: bytearray):
        """Handle incoming notifications."""
        rx_packet = PacketFactory.from_rx_data(data)
        self._log_packet("RX", rx_packet)

        if not self._handle_duplicates_and_checksum(rx_packet, data):
            return

        opcode = rx_packet.opcode
        self._cache_log_count(rx_packet)

        if isinstance(rx_packet, ErrorResponsePacket):
            _LOGGER.error("Boks reported error: %s", rx_packet.error_type)

        if isinstance(rx_packet, NfcScanResultPacket):
            self._handle_scanned_tag(rx_packet.uid, rx_packet.status)

        # Handle door status and triggers
        door_update = self._handle_door_logic(rx_packet)
        if door_update:
            self._dispatch_door_update()

        # Resolve async waiting tasks
        self._resolve_futures(opcode, data)

        # Legacy notification callback
        if self._notify_callback:
            self._notify_callback(opcode, data)

        # Direct opcode callbacks
        self._dispatch_callbacks(opcode, data)

    def _handle_duplicates_and_checksum(self, packet: BoksRXPacket, data: bytearray) -> bool:
        """Verify checksum and log duplicates. Returns True if packet should be processed."""
        if not packet.verify_checksum():
            _LOGGER.error("Invalid checksum in notification: %s", packet.to_bytes().hex())
            return False

        # Log duplicate notifications
        current_time = time.time()
        last_data = getattr(self, '_last_notification_data', None)
        last_time = getattr(self, '_last_notification_time', 0)

        if last_data == data and (current_time - last_time) < 1.0:
            _LOGGER.debug("Potential duplicate notification received")

        self._last_notification_data = data
        self._last_notification_time = current_time
        return True

    def _cache_log_count(self, packet: BoksRXPacket):
        """Update log count cache if packet contains it."""
        if packet.opcode == BoksNotificationOpcode.NOTIFY_LOGS_COUNT and hasattr(packet, "count"):
            self._last_log_count_value = packet.count
            self._last_log_count_ts = time.time()
            _LOGGER.debug("Cached Log Count: %d", packet.count)

    def _handle_door_logic(self, packet: BoksRXPacket) -> bool:
        """Update door status based on packet. Returns True if status changed."""
        if isinstance(packet, DoorStatusPacket):
            self._door_status = packet.is_open
            return True

        if isinstance(packet, DoorClosedPacket):
            self._door_status = False
            self._last_door_close_time = time.time()
            if getattr(packet, "age", 0) < 10:
                self._refresh_needed = True
            return True

        if isinstance(packet, (DoorOpenedPacket, CodeBleValidPacket, CodeKeyValidPacket, NfcOpeningPacket, KeyOpeningPacket)):
            self._door_status = True
            self._last_door_open_time = time.time()
            if getattr(packet, "age", 0) < 10:
                self._refresh_needed = True
            return True

        return False

    def _dispatch_door_update(self):
        """Trigger door events and callbacks."""
        self._door_event.set()
        _LOGGER.debug("Door status update: %s", "Open" if self._door_status else "Closed")
        if self._status_callback:
            self._status_callback({"door_open": self._door_status})

    def _resolve_futures(self, opcode: int, data: bytearray):
        """Complete any pending futures waiting for this opcode."""
        opcode_str = str(opcode)
        for key, future in list(self._response_futures.items()):
            if not future.done() and opcode_str in key.split(","):
                future.set_result(data)
                del self._response_futures[key]
            elif future.done() and key in self._response_futures:
                del self._response_futures[key]

    def _dispatch_callbacks(self, opcode: int, data: bytearray):
        """Invoke registered opcode callbacks."""
        if opcode in self._response_callbacks:
            try:
                self._response_callbacks[opcode](data)
            except Exception as e:
                _LOGGER.error("Error in callback for opcode 0x%02X: %s", opcode, e)

        if opcode in self._opcode_callbacks:
            for callback in self._opcode_callbacks[opcode][:]:
                try:
                    callback(data)
                except Exception as e:
                    _LOGGER.error("Error in opcode callback for opcode 0x%02X: %s", opcode, e)

    async def wait_for_door_closed(self, timeout: float = TIMEOUT_DOOR_CLOSE) -> bool:
        """Wait for the door to be closed."""
        if not self.is_connected:
             _LOGGER.warning("Cannot wait for door close: Not connected.")
             return False

        try:
            async with asyncio.timeout(timeout):
                while self._door_status:
                    self._door_event.clear()
                    await self._door_event.wait()
        except TimeoutError:
            pass

        return not self._door_status

    async def get_battery_level(self) -> int:
        """Get battery level."""
        async with self._lock:
            await self._connect()
            try:
                return await self._get_battery_level()
            finally:
                await self._disconnect()

    async def _get_battery_level(self) -> int:
        """Internal get battery level."""
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
        async with self._lock:
            await self._connect()
            try:
                return await self._get_battery_stats()
            finally:
                await self._disconnect()

    async def _get_battery_stats(self) -> dict | None:
        """Internal get battery stats."""
        if self._client is None:
            return None
        try:
            payload = await self._client.read_gatt_char(BoksServiceUUID.BATTERY_CHARACTERISTIC)
            stats = BoksProtocol.parse_battery_stats(payload)
            if stats:
                _LOGGER.debug("Battery stats (Custom): %s", stats)
                return stats
        except Exception as e:
            _LOGGER.debug("Custom battery char read failed: %s", e)
        try:
            payload = await self._client.read_gatt_char(BoksServiceUUID.BATTERY_LEVEL_CHARACTERISTIC)
            if len(payload) == 1:
                return {"format": "measure-single", "level_single": payload[0], "temperature": None}
        except Exception as e:
             _LOGGER.warning("Failed to read standard battery: %s", e)
        return None

    async def get_internal_firmware_revision(self) -> str | None:
        """Get internal firmware revision."""
        async with self._lock:
            await self._connect()
            try:
                if self._client is None:
                    return None
                try:
                    payload = await self._client.read_gatt_char(BoksServiceUUID.INTERNAL_FIRMWARE_REVISION_CHARACTERISTIC)
                    return payload.decode('ascii').strip()
                except Exception as e:
                    _LOGGER.debug("Failed to read firmware revision: %s", e)
                return None
            finally:
                await self._disconnect()

    async def get_door_status(self) -> bool:
        """Get current door status."""
        from ..packets.rx.door_status import DoorStatusPacket
        from ..packets.tx.ask_door_status import AskDoorStatusPacket
        packet = AskDoorStatusPacket()
        resp = await self.send_packet(packet, wait_for_opcodes=[BoksNotificationOpcode.NOTIFY_DOOR_STATUS, BoksNotificationOpcode.ANSWER_DOOR_STATUS])
        if isinstance(resp, DoorStatusPacket):
            self._door_status = resp.is_open
        return self._door_status

    async def get_device_information(self) -> dict:
        """Read device information."""
        async with self._lock:
            await self._connect()
            try:
                if self._client is None:
                    return {}
                info = {}
                chars = {
                    BoksServiceUUID.MANUFACTURER_NAME_CHARACTERISTIC: "manufacturer_name",
                    BoksServiceUUID.MODEL_NUMBER_CHARACTERISTIC: "model_number",
                    BoksServiceUUID.SERIAL_NUMBER_CHARACTERISTIC: "serial_number",
                    BoksServiceUUID.SOFTWARE_REVISION_CHARACTERISTIC: "software_revision",
                    BoksServiceUUID.HARDWARE_REVISION_CHARACTERISTIC: "hardware_revision",
                    BoksServiceUUID.INTERNAL_FIRMWARE_REVISION_CHARACTERISTIC: "firmware_revision",
                    BoksServiceUUID.SYSTEM_ID_CHARACTERISTIC: "system_id",
                }
                for char_uuid, key in chars.items():
                    try:
                        payload = await self._client.read_gatt_char(char_uuid)
                        if key == "system_id":
                            info[key] = payload.hex()
                        else:
                            info[key] = payload.decode('ascii').strip()
                    except Exception as e:
                        _LOGGER.debug("Failed to read %s: %s", key, e)
                return info
            finally:
                await self._disconnect()

    def _validate_pin(self, code: str) -> str:
        """Validate PIN code format (6 chars, 0-9, A, B)."""
        if not code:
            raise BoksError("pin_code_invalid")

        # Clean code
        clean_code = str(code).upper().strip()

        if len(clean_code) != 6:
            raise BoksError("pin_code_invalid_length")

        valid_chars = "0123456789AB"
        if not all(c in valid_chars for c in clean_code):
            raise BoksError("invalid_code_format")

        return clean_code

    async def open_door(self, code: str = None) -> bool:
        """Open the door."""
        if code:
            code = self._validate_pin(code)

        from ..packets.tx.open_door import OpenDoorPacket
        packet = OpenDoorPacket(code or "")
        resp = await self.send_packet(packet, wait_for_opcodes=[BoksNotificationOpcode.VALID_OPEN_CODE, BoksNotificationOpcode.INVALID_OPEN_CODE, BoksNotificationOpcode.ERROR_UNAUTHORIZED])
        if resp and resp.opcode == BoksNotificationOpcode.VALID_OPEN_CODE:
            self._door_status = True
            return True
        elif resp and resp.opcode == BoksNotificationOpcode.ERROR_UNAUTHORIZED:
             raise BoksAuthError("unauthorized")
        return False

    async def get_code_counts(self) -> dict:
        """Get code counts."""
        from ..packets.rx.code_counts import CodeCountsPacket
        from ..packets.tx.count_codes import CountCodesPacket
        packet = CountCodesPacket()
        resp = await self.send_packet(packet, wait_for_opcodes=[BoksNotificationOpcode.NOTIFY_CODES_COUNT])
        if isinstance(resp, CodeCountsPacket):
            return {"master": resp.master_count, "single_use": resp.single_use_count}
        return {}

    async def get_logs_count(self) -> int:
        """Get logs count."""
        async with self._lock:
            await self._connect()
            try:
                return await self._get_logs_count()
            finally:
                await self._disconnect()

    async def _get_logs_count(self) -> int:
        """Internal get logs count with stabilization."""
        from ..packets.rx.log_count import LogCountPacket
        from ..packets.tx.get_logs_count import GetLogsCountPacket

        # Check cache first
        if self._last_log_count_value is not None and (time.time() - self._last_log_count_ts) < 3.0:
            _LOGGER.debug("Using cached log count: %d", self._last_log_count_value)
            return self._last_log_count_value

        counts: list[int] = []

        def handle_count(data: bytearray):
            p = PacketFactory.from_rx_data(data)
            if isinstance(p, LogCountPacket):
                counts.append(p.count)

        # Register a temporary listener to collect all responses for a short window
        self.register_opcode_callback(BoksNotificationOpcode.NOTIFY_LOGS_COUNT, handle_count)
        try:
            packet = GetLogsCountPacket()

            # 1. Wait for the FIRST response reliably using the standard mechanism
            # This ensures we don't exit if the device takes >100ms to reply
            first_resp = await self._send_packet(packet, wait_for_opcodes=[BoksNotificationOpcode.NOTIFY_LOGS_COUNT])

            # If we got a response via send_packet, ensure it's in our counts list
            # (The callback might have caught it too, but duplication is fine since we take max)
            if isinstance(first_resp, LogCountPacket):
                counts.append(first_resp.count)

            # 2. Wait a short window for potential subsequent "correction" responses (0 then 3)
            await asyncio.sleep(TIMEOUT_LOG_COUNT_STABILIZATION)

            if counts:
                max_count = max(counts)
                if len(counts) > 1:
                    _LOGGER.debug("Stabilized log count: %d (from multiple responses: %s)", max_count, counts)
                return max_count
        except Exception as e:
            _LOGGER.warning("Error during stabilized log count fetch: %s", e)
        finally:
            self.unregister_opcode_callback(BoksNotificationOpcode.NOTIFY_LOGS_COUNT, handle_count)

        return 0

    async def get_logs(self, count: int) -> list[dict]:
        """Retrieve logs."""
        async with self._lock:
            await self._connect()
            try:
                return await self._get_logs(count)
            finally:
                await self._disconnect()

    async def _get_logs(self, count: int) -> list[dict]:
        """Internal retrieve logs."""
        from ..packets.tx.request_logs import RequestLogsPacket
        if count <= 0:
            return []
        packet = RequestLogsPacket()
        logs = []
        logs_received_event = asyncio.Event()
        def log_callback(opcode, data):
            if opcode == BoksHistoryEvent.LOG_END_HISTORY:
                logs_received_event.set()
            elif opcode in list(BoksHistoryEvent):
                p = PacketFactory.from_rx_data(data)
                if p:
                    logs.append({"opcode": p.opcode, "payload": p.payload, "timestamp": int(time.time()) - getattr(p, 'age', 0), "event_type": p.event_type, "description": p.opcode.name.lower() if hasattr(p.opcode, 'name') else "unknown", "extra_data": p.extra_data})
            elif opcode == BoksNotificationOpcode.NOTIFY_LOGS_COUNT and len(data) >= 4 and data[2] == 0 and data[3] == 0:
                logs_received_event.set()
        self._notify_callback = log_callback
        try:
            await self._send_packet(packet)
            await asyncio.wait_for(logs_received_event.wait(), timeout=5.0 + (count * 1.5))
        except TimeoutError:
            _LOGGER.warning("Timeout waiting for logs. Received %d/%d", len(logs), count)
        finally:
            self._notify_callback = None

        # We just retrieved logs, so we don't need another refresh on disconnect
        self._refresh_needed = False
        return logs

    async def create_pin_code(self, code: str, code_type: str, index: int = 0) -> str:
        """Create a PIN code."""
        if not self._config_key_str:
            raise BoksAuthError("config_key_required")

        # Validate format
        code = self._validate_pin(code)

        if code_type == "master":
            from ..packets.tx.create_master_code import CreateMasterCodePacket
            packet = CreateMasterCodePacket(self._config_key_str, code, index)
        elif code_type == "single":
            from ..packets.tx.create_single_code import CreateSingleUseCodePacket
            packet = CreateSingleUseCodePacket(self._config_key_str, code)
        else:
            from ..packets.tx.create_multi_code import CreateMultiUseCodePacket
            packet = CreateMultiUseCodePacket(self._config_key_str, code)
        resp = await self.send_packet(packet, wait_for_opcodes=[BoksNotificationOpcode.CODE_OPERATION_SUCCESS, BoksNotificationOpcode.CODE_OPERATION_ERROR, BoksNotificationOpcode.ERROR_UNAUTHORIZED])
        if resp and resp.opcode == BoksNotificationOpcode.CODE_OPERATION_SUCCESS:
            return code
        elif resp and resp.opcode == BoksNotificationOpcode.ERROR_UNAUTHORIZED:
             raise BoksAuthError("unauthorized")
        raise BoksError("create_code_failed")

    async def delete_pin_code(self, type: str, index_or_code: Any) -> bool:
        """Delete a PIN code."""
        if not self._config_key_str:
            raise BoksAuthError("config_key_required")
        if type == "master":
            from ..packets.tx.delete_master_code import DeleteMasterCodePacket
            packet = DeleteMasterCodePacket(self._config_key_str, int(index_or_code))
        elif type == "single":
            from ..packets.tx.delete_single_code import DeleteSingleUseCodePacket
            packet = DeleteSingleUseCodePacket(self._config_key_str, str(index_or_code))
        else:
            from ..packets.tx.delete_multi_code import DeleteMultiUseCodePacket
            packet = DeleteMultiUseCodePacket(self._config_key_str, str(index_or_code))
        resp = await self.send_packet(packet, wait_for_opcodes=[BoksNotificationOpcode.CODE_OPERATION_SUCCESS, BoksNotificationOpcode.CODE_OPERATION_ERROR, BoksNotificationOpcode.ERROR_UNAUTHORIZED])
        return resp is not None and resp.opcode == BoksNotificationOpcode.CODE_OPERATION_SUCCESS

    async def set_configuration(self, config_type: int, value: bool) -> bool:
        """Set device configuration."""
        if not self._config_key_str:
            raise BoksAuthError("config_key_required")
        from ..packets.tx.set_configuration import SetConfigurationPacket
        packet = SetConfigurationPacket(self._config_key_str, config_type, value)
        resp = await self.send_packet(packet, wait_for_opcodes=[BoksNotificationOpcode.NOTIFY_SET_CONFIGURATION_SUCCESS, BoksNotificationOpcode.ERROR_UNAUTHORIZED, BoksNotificationOpcode.ERROR_BAD_REQUEST])
        if resp and resp.opcode == BoksNotificationOpcode.NOTIFY_SET_CONFIGURATION_SUCCESS:
            return True
        elif resp and resp.opcode == BoksNotificationOpcode.ERROR_UNAUTHORIZED:
             raise BoksAuthError("unauthorized")
        raise BoksError("set_configuration_failed", {"config_type": str(config_type)})

    async def nfc_scan_start(self) -> bool:
        """Start NFC scan mode."""
        if not self._config_key_str:
            raise BoksAuthError("config_key_required")
        from ..packets.tx.nfc_scan_start import NfcScanStartPacket
        packet = NfcScanStartPacket(self._config_key_str)
        # We wait for success ACK OR immediate result (if tag already on reader)
        resp = await self.send_packet(
            packet,
            wait_for_opcodes=[
                BoksNotificationOpcode.CODE_OPERATION_SUCCESS,
                BoksNotificationOpcode.NOTIFY_NFC_TAG_FOUND,
                BoksNotificationOpcode.ERROR_NFC_TAG_ALREADY_EXISTS_SCAN,
                BoksNotificationOpcode.ERROR_NFC_SCAN_TIMEOUT,
                BoksNotificationOpcode.ERROR_UNAUTHORIZED,
                BoksNotificationOpcode.ERROR_BAD_REQUEST
            ]
        )
        return resp is not None and resp.opcode in (
            BoksNotificationOpcode.CODE_OPERATION_SUCCESS,
            BoksNotificationOpcode.NOTIFY_NFC_TAG_FOUND,
            BoksNotificationOpcode.ERROR_NFC_TAG_ALREADY_EXISTS_SCAN
        )

    def _handle_scanned_tag(self, uid: str | None, status: str):
        """Handle a scanned tag."""
        if _LOGGER.isEnabledFor(logging.INFO):
            log_uid = BoksAnonymizer.anonymize_uid(uid, self.anonymize_logs)
            _LOGGER.info("NFC Tag Scanned: %s (Status: %s)", log_uid, status)
        self.hass.async_create_task(self._async_handle_scanned_tag(uid, status))

    async def _async_handle_scanned_tag(self, uid: str | None, status: str):
        """Async handle scanned tag."""
        coordinator = None
        for _entry_id, coord in self.hass.data.get(DOMAIN, {}).items():
            if hasattr(coord, "ble_device") and coord.ble_device == self:
                coordinator = coord
                break
                break
        if not coordinator:
            _LOGGER.warning("Could not find coordinator for NFC notification")
            return
        display_uid = BoksAnonymizer.anonymize_uid(uid, self.anonymize_logs)
        tag_name = None
        if uid and "tag" in self.hass.data:
            try:
                tag_id_lookup = uid.replace(":", "").upper()
                try:
                    from homeassistant.components.tag import async_scan_tag
                    await async_scan_tag(self.hass, tag_id_lookup, self.address)
                except Exception as e:
                    _LOGGER.debug("Could not trigger async_scan_tag: %s", e)
                tag_manager = self.hass.data["tag"]
                tags_helper = tag_manager.get("tags") if isinstance(tag_manager, dict) else None
                tag_info = None
                if tags_helper and tag_id_lookup in tags_helper.data:
                    tag_info = tags_helper.data[tag_id_lookup]
                if not tag_info and hasattr(tag_manager, "async_get_tag"):
                    tag_info = await tag_manager.async_get_tag(tag_id_lookup)
                if tag_info:
                    tag_name = tag_info.get("name")
            except Exception as e:
                _LOGGER.debug("Could not lookup tag name: %s", e)
        if status == "found":
            title = coordinator.get_text("common", "nfc_tag_found_title")
            message = coordinator.get_text("common", "nfc_tag_found_msg_named" if tag_name else "nfc_tag_found_msg", name=tag_name, uid=display_uid)
            notification_id = f"boks_nfc_found_{uid}"
        elif status == "already_exists":
            title = coordinator.get_text("common", "nfc_tag_exists_title")
            if tag_name:
                message = coordinator.get_text("common", "nfc_tag_exists_msg_named", name=tag_name, uid=display_uid)
            elif uid:
                message = coordinator.get_text("common", "nfc_tag_exists_msg", uid=display_uid)
            else:
                message = coordinator.get_text("common", "nfc_tag_exists_msg_unknown")
            notification_id = f"boks_nfc_exists_{uid}" if uid else "boks_nfc_exists_unknown"
        elif status == "timeout":
            title = coordinator.get_text("common", "nfc_scan_timeout_title")
            message = coordinator.get_text("common", "nfc_scan_timeout_msg")
            notification_id = "boks_nfc_timeout"
        else:
            return
        if not tag_name and status == "found":
            help_text = coordinator.get_text("common", "nfc_tag_found_register_help")
            message += f"\n\n{help_text}"
        _LOGGER.debug("Creating persistent notification: %s - %s", title, message)
        await self.hass.services.async_call("persistent_notification", "create", {"title": title, "message": message, "notification_id": notification_id})

    async def nfc_register_tag(self, uid: str) -> bool:
        """Register NFC tag."""
        if not self._config_key_str:
            raise BoksAuthError("config_key_required")
        from ..packets.tx.register_nfc_tag import RegisterNfcTagPacket
        packet = RegisterNfcTagPacket(self._config_key_str, uid)
        resp = await self.send_packet(packet, wait_for_opcodes=[BoksNotificationOpcode.NOTIFY_NFC_TAG_REGISTERED, BoksNotificationOpcode.ERROR_NFC_TAG_ALREADY_EXISTS_REGISTER, BoksNotificationOpcode.ERROR_UNAUTHORIZED, BoksNotificationOpcode.ERROR_BAD_REQUEST])
        if resp and resp.opcode == BoksNotificationOpcode.NOTIFY_NFC_TAG_REGISTERED:
            return True
        elif resp and resp.opcode == BoksNotificationOpcode.ERROR_NFC_TAG_ALREADY_EXISTS_REGISTER:
            raise BoksError("nfc_tag_already_exists")
        elif resp and resp.opcode == BoksNotificationOpcode.ERROR_UNAUTHORIZED:
            raise BoksAuthError("unauthorized")
        return False

    async def nfc_unregister_tag(self, uid: str) -> bool:
        """Unregister NFC tag."""
        if not self._config_key_str:
            raise BoksAuthError("config_key_required")
        from ..packets.tx.nfc_unregister_tag import NfcUnregisterTagPacket
        packet = NfcUnregisterTagPacket(self._config_key_str, uid)
        resp = await self.send_packet(packet, wait_for_opcodes=[BoksNotificationOpcode.NOTIFY_NFC_TAG_UNREGISTERED, BoksNotificationOpcode.ERROR_UNAUTHORIZED, BoksNotificationOpcode.ERROR_BAD_REQUEST])
        return resp is not None and resp.opcode == BoksNotificationOpcode.NOTIFY_NFC_TAG_UNREGISTERED
