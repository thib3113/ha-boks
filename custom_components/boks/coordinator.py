"""DataUpdateCoordinator for Boks."""

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import translation  # Import translation helper
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .ble import BoksBluetoothDevice
from .codes.codes_controller import BoksCodesController
from .commands.commands_controller import BoksCommandsController
from .const import (
    BOKS_HARDWARE_INFO,
    CONF_ANONYMIZE_LOGS,
    CONF_CONFIG_KEY,
    DEFAULT_FULL_REFRESH_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_LOGS_RETRIEVED,
    TIMEOUT_BLE_CONNECTION,
)
from .errors import BoksError
from .logic.anonymizer import BoksAnonymizer
from .logic.log_processor import BoksLogProcessor
from .nfc.nfc_controller import BoksNfcController
from .packets.base import BoksRXPacket
from .parcels.parcels_controller import BoksParcelsController
from .updates.logic import BoksUpdateController
from .util import process_device_info

_LOGGER = logging.getLogger(__name__)

class BoksDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Boks data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize global Boks data updater."""
        self.ble_device = BoksBluetoothDevice(
            hass=hass,
            address=entry.data[CONF_ADDRESS],
            config_key=entry.data.get(CONF_CONFIG_KEY),
            anonymize_logs=entry.options.get(CONF_ANONYMIZE_LOGS, False)
        )
        self.ble_device.set_coordinator(self)
        self.updates = BoksUpdateController(hass, self)
        self.nfc = BoksNfcController(hass, self)
        self.codes = BoksCodesController(hass, self)
        self.parcels = BoksParcelsController(hass, self)
        self.commands = BoksCommandsController(hass, self)
        # Initialize log processor
        self.log_processor = BoksLogProcessor(hass, entry.data[CONF_ADDRESS])

        # Register callback for push updates (door status, battery info)
        self.ble_device.register_status_callback(self._handle_status_update)

        self.entry = entry
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("BoksDataUpdateCoordinator initialized with Address: %s, Config Key Present: %s",
                           BoksAnonymizer.anonymize_mac(entry.data[CONF_ADDRESS], self.ble_device.anonymize_logs),
                           bool(entry.data.get(CONF_CONFIG_KEY)))
        self._last_battery_update = None
        self.full_refresh_interval_hours = entry.options.get("full_refresh_interval", DEFAULT_FULL_REFRESH_INTERVAL)
        # Set the full refresh interval on the BLE device
        self.ble_device.set_full_refresh_interval(self.full_refresh_interval_hours)

        # Get scan interval from options, default to constant
        scan_interval_minutes = entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
        if scan_interval_minutes == 0:
            update_interval = None
        else:
            update_interval = timedelta(minutes=scan_interval_minutes)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.data = {} # Initialize data to an empty dictionary after super init
        self._maintenance_status = {"running": False}
        self._device_info = None
        self._translations: dict[str, str] = {}

    @property
    def maintenance_status(self):
        return self._maintenance_status

    def set_translations(self, translations: dict):
        """Set translations for the coordinator."""
        self._translations = translations

    def get_text(self, category: str, key: str, **kwargs) -> str:
        """Get a translated string."""
        base_key = f"component.{DOMAIN}.{category}.{key}"

        # Try direct key first
        text = self._translations.get(base_key)

        # If not found (common for exceptions which have nested 'message'), try appending .message
        if not text:
            text = self._translations.get(f"{base_key}.message")

        if text:
            # Simple format if needed
            if kwargs:
                try:
                    return text.format(**kwargs)
                except Exception:
                    return text
            return text
        return key

    async def get_or_fetch_device_info(self) -> dict:
        """
        Get device info from cache, live fetch, or registry fallback.
        Returns a dict with 'sw_version', 'hw_version', 'internal_revision'.
        """
        # 1. Cache
        info = {
            "sw_version": self.device_info.get("sw_version"),
            "hw_version": self.device_info.get("hw_version"),
            "internal_revision": self.data.get("device_info_service", {}).get("firmware_revision")
        }

        # 2. Live Fetch if missing
        if not info["internal_revision"]:
            try:
                _LOGGER.debug("Internal revision not in cache, trying live fetch...")
                device_info_raw = await self.ble_device.get_device_information()
                if device_info_raw:
                    info["internal_revision"] = device_info_raw.get("firmware_revision")
                    # Update other fields if available and missing
                    if not info["sw_version"]:
                        info["sw_version"] = device_info_raw.get("software_revision")
                    if not info["hw_version"]:
                        info["hw_version"] = device_info_raw.get("hardware_revision")
            except Exception as e:
                _LOGGER.warning("Failed to fetch live device information (device likely offline): %s", e)

        # 3. Registry Fallback if still missing
        if not info["internal_revision"]:
            _LOGGER.debug("Live fetch failed, trying Device Registry fallback...")
            dev_reg = dr.async_get(self.hass)
            device_entry = dev_reg.async_get_device(identifiers={(DOMAIN, self.ble_device.address)})

            if device_entry:
                if not info["sw_version"]:
                    info["sw_version"] = device_entry.sw_version

                if not info["hw_version"]:
                    info["hw_version"] = device_entry.hw_version

                # Deduce internal revision
                if info["hw_version"]:
                    for rev_id, hw_data in BOKS_HARDWARE_INFO.items():
                        if hw_data["hw_version"] == info["hw_version"]:
                            info["internal_revision"] = rev_id
                            _LOGGER.info("Offline recovery: Deduced internal revision '%s' from registry hardware version '%s'", rev_id, info["hw_version"])
                            break

        return info

    async def async_enrich_log_entry(self, log: BoksRXPacket | dict, translations: dict[str, str] = None) -> dict:
        """Enrich a log entry using the dedicated processor."""
        return await self.log_processor.async_enrich_log_entry(log, translations or self._translations)


    @property
    def device_info(self):
        """Return device info."""
        if self._device_info is None:
            # Get base info using shared utility
            device_info_service = self.data.get("device_info_service") if self.data else None
            self._device_info = process_device_info(self.entry.data, device_info_service)
        return self._device_info

    def set_maintenance_status(self, running: bool, current_index: int = 0, total_to_clean: int = 0, cleaned_count: int = 0, error: str = None):
        """Update the maintenance status and notify listeners."""

        message = ""
        if error:
             # Errors are passed raw or should be pre-translated, but for safety we treat as raw string if passed here
             # Ideally the caller passes a translation key but 'error' is dynamic.
             message = self.get_text("exceptions", "maintenance_failed_msg", error=error)
        elif running:
             message = self.get_text("common", "maintenance_progress_msg",
                                     current=current_index,
                                     total=total_to_clean,
                                     cleaned=cleaned_count)
        else:
             # Finished or Idle
             if total_to_clean > 0 and current_index >= total_to_clean:
                 message = self.get_text("common", "maintenance_finished_msg", cleaned=cleaned_count)
             else:
                 message = self.get_text("common", "maintenance_idle_msg")

        self._maintenance_status = {
            "running": running,
            "current_index": current_index,
            "total_to_clean": total_to_clean,
            "cleaned_count": cleaned_count,
            "progress": int(current_index / total_to_clean * 100) if total_to_clean > 0 else 0,
            "last_cleaned": current_index - 1 if current_index > 0 else 0,
            "message": message
        }
        self.async_set_updated_data(self.data)

    def _handle_status_update(self, status_data: dict):
        """Handle push updates from the device."""
        if self.data is None:
            self.data = {}

        # If there are raw logs, process them
        if "latest_logs_raw" in status_data:
            logs_raw = status_data.pop("latest_logs_raw")
            self.hass.async_create_task(self._process_pushed_logs(logs_raw))

        self.data.update(status_data)
        self.data["last_connection"] = dt_util.now().isoformat()

        # Persist battery format if detected
        if "battery_stats" in status_data:
            stats = status_data["battery_stats"]
            new_format = stats.get("format")
            if new_format and new_format != "unknown":
                current_stored_format = self.entry.data.get("battery_format")
                if new_format != current_stored_format:
                    _LOGGER.info("Detected new battery format: %s. Persisting to config.", new_format)
                    new_data = dict(self.entry.data)
                    new_data["battery_format"] = new_format
                    self.hass.config_entries.async_update_entry(self.entry, data=new_data)

        self.async_set_updated_data(self.data)

    async def _process_pushed_logs(self, logs_raw: list[dict]):
        """Process logs that were pushed via status update."""
        if not logs_raw:
            return

        _LOGGER.debug("Processing %d pushed logs", len(logs_raw))
        try:
            translations = await translation.async_get_translations(self.hass, self.hass.config.language, "entity", {DOMAIN})
        except Exception:
            translations = {}

        event_data = {
            "device_id": self.entry.entry_id,
            "address": self.entry.data[CONF_ADDRESS],
            "logs": []
        }

        for log in logs_raw:
            try:
                log_entry = await self.async_enrich_log_entry(log, translations)
                event_data["logs"].append(log_entry)
            except Exception as e:
                _LOGGER.warning("Error processing pushed log: %s", e)

        if event_data["logs"]:
            self.hass.bus.async_fire(EVENT_LOGS_RETRIEVED, event_data)
            self.data["latest_logs"] = event_data["logs"]
            self.data["last_log_fetch_ts"] = datetime.now().isoformat()
            self.async_set_updated_data(self.data)


    async def async_sync_logs(self, update_state: bool = True) -> dict:
        """
        Fetch logs from the device.
        If update_state is True, it updates the coordinator data and notifies listeners.
        Returns a dict with 'latest_logs' and 'last_log_fetch_ts' if successful, else empty dict.
        """
        result = {}
        try:
            await self.ble_device.connect()

            # Retrieve log count (this method handles caching internally to avoid redundant BLE calls)
            log_count = await self.ble_device.get_logs_count()

            if log_count > 0:
                _LOGGER.info("Found %d logs. Downloading...", log_count)
                logs_raw = await self.ble_device.get_logs(log_count)

                if logs_raw:
                    result = await self._process_logs_data(logs_raw, update_state)
            else:
                _LOGGER.debug("No logs to retrieve.")

        except Exception as e:
            _LOGGER.warning("Failed to sync logs: %s", e)
        finally:
            await asyncio.shield(self.ble_device.disconnect())

        return result

    async def _process_logs_data(self, logs_raw: list[dict], update_state: bool) -> dict:
        """Process, enrich and fire events for retrieved logs."""
        # Filter and log
        valid_logs = [log for log in logs_raw if log is not None]
        if len(valid_logs) != len(logs_raw):
            _LOGGER.warning("Filtered out %d None log entries", len(logs_raw) - len(valid_logs))

        # Enrich logs
        enriched_logs, has_power_on = await self._enrich_logs(valid_logs)

        # Resolve real Device ID from registry
        device_registry = dr.async_get(self.hass)
        device_entry = device_registry.async_get_device(identifiers={(DOMAIN, self.entry.data[CONF_ADDRESS])})
        real_device_id = device_entry.id if device_entry else None

        # Fire event with correct IDs
        event_data = {
            "device_id": real_device_id,           # Real Device Registry ID
            "config_entry_id": self.entry.entry_id, # Config Entry ID
            "address": self.entry.data[CONF_ADDRESS],
            "logs": enriched_logs
        }
        self.hass.bus.async_fire(EVENT_LOGS_RETRIEVED, event_data)

        # Final checks
        if has_power_on:
            _LOGGER.info("Power ON detected in logs, polling live door status...")
            self.data["door_open"] = await self.ble_device.get_door_status()

        # Update results
        result = {
            "latest_logs": enriched_logs,
            "last_log_fetch_ts": datetime.now().isoformat()
        }

        if update_state:
            self.data.update(result)
            self.async_set_updated_data(self.data)

        return result

    async def _enrich_logs(self, logs: list[dict]) -> tuple[list[dict], bool]:
        """Enrich raw logs with translations and metadata."""
        try:
            translations = await translation.async_get_translations(self.hass, self.hass.config.language, "entity", {DOMAIN})
        except Exception as e:
            _LOGGER.warning("Failed to load translations: %s", e)
            translations = {}

        enriched = []
        has_power_on = False

        for i, log in enumerate(logs):
            try:
                entry = await self.async_enrich_log_entry(log, translations)
                enriched.append(entry)
                if entry.get("event_type") == "power_on":
                    has_power_on = True
            except Exception as e:
                _LOGGER.warning("Error processing log at index %d: %s", i, e)

        return enriched, has_power_on

    async def _async_update_data(self) -> dict:
        """Fetch data from the Boks."""
        data = self.data if self.data else {}
        try:
            async with asyncio.timeout(TIMEOUT_BLE_CONNECTION):
                try:
                    await self.ble_device.connect()
                    now = datetime.now()

                    # 1. Battery (Initial only)
                    if "battery_level" not in data:
                        await self._fetch_initial_battery_data(data, now)
                    else:
                        _LOGGER.debug("Battery fetch skipped (handled by door events).")

                    # 2. Code Counts
                    await self._fetch_code_counts(data)

                    # 3. Device Information
                    await self._fetch_device_info(data, now)

                    # 4. Logs
                    await self._fetch_logs_and_sync(data)

                    data["last_connection"] = dt_util.now().isoformat()

                finally:
                    await asyncio.shield(self.ble_device.disconnect())

        except TimeoutError as e:
            _LOGGER.error("Timeout during Boks BLE data update")
            raise UpdateFailed("Timeout during Boks BLE data update") from e
        except UpdateFailed:
            raise
        except Exception as err:
            if self.data:
                _LOGGER.warning("Update failed, keeping old data: %s", err)
                return self.data
            raise UpdateFailed(f"Error communicating with Boks: {err}") from err

        return data

    async def _fetch_initial_battery_data(self, data: dict, now: datetime):
        """Fetch initial battery level and stats."""
        _LOGGER.debug("Fetching battery level and stats (Initial)...")
        try:
            data["battery_level"] = await self.ble_device.get_battery_level()
            self._last_battery_update = now
        except Exception as e:
            _LOGGER.warning("Failed to fetch battery level: %s", e)

        try:
            battery_stats = await self.ble_device.get_battery_stats()
            if battery_stats:
                data["battery_stats"] = battery_stats
                if battery_stats.get("temperature") is not None:
                    data["battery_temperature"] = battery_stats["temperature"]
        except Exception as e:
            _LOGGER.warning("Failed to fetch battery stats: %s", e)

    async def _fetch_code_counts(self, data: dict):
        """Fetch current code counts from device."""
        _LOGGER.debug("Fetching code counts...")
        try:
            counts = await self.ble_device.get_code_counts()
            data.update(counts)
        except (TimeoutError, BoksError) as e:
            _LOGGER.warning("Could not fetch code counts: %s", e)

    async def _fetch_device_info(self, data: dict, now: datetime):
        """Fetch device information with throttling."""
        should_fetch = True
        if "device_info_service" in data:
             last_fetch = data.get("last_device_info_fetch")
             if last_fetch:
                 last_fetch_dt = datetime.fromisoformat(last_fetch)
                 interval = self.full_refresh_interval_hours * 2
                 if (now - last_fetch_dt) < timedelta(hours=interval):
                     should_fetch = False
                     _LOGGER.debug("Skipping device info update (last update < %dh ago)", interval)

        if not should_fetch:
            return

        _LOGGER.debug("Fetching device information...")
        try:
            device_info = await self.ble_device.get_device_information()
            data["device_info_service"] = device_info
            data["last_device_info_fetch"] = now.isoformat()
            self._update_device_registry(device_info)
        except Exception as e:
            _LOGGER.warning("Failed to fetch device information: %s", e)

    def _update_device_registry(self, device_info: dict):
        """Update Home Assistant device registry with hardware/software info."""
        device_registry = dr.async_get(self.hass)
        device_entry = device_registry.async_get_device(
            identifiers={(DOMAIN, self.entry.data[CONF_ADDRESS])},
        )

        if device_entry:
            processed_info = process_device_info(self.entry.data, device_info)
            update_kwargs = {
                k: processed_info[k]
                for k in ["sw_version", "hw_version", "manufacturer", "model"]
                if k in processed_info
            }
            if update_kwargs:
                device_registry.async_update_device(device_entry.id, **update_kwargs)
                _LOGGER.info("Device registry updated with new info: %s", update_kwargs)

    async def _fetch_logs_and_sync(self, data: dict):
        """Auto-download logs and update coordinator data."""
        logs_data = await self.async_sync_logs(update_state=False)
        if logs_data:
            data.update(logs_data)

    def register_opcode_callback(self, opcode: int, callback: Callable[[bytearray], None]) -> None:
        """Register a callback for a specific opcode."""
        self.ble_device.register_opcode_callback(opcode, callback)

    def unregister_opcode_callback(self, opcode: int, callback: Callable[[bytearray], None]) -> None:
        """Unregister a callback for a specific opcode."""
        self.ble_device.unregister_opcode_callback(opcode, callback)



