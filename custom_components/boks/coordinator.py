"""DataUpdateCoordinator for Boks."""

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import translation  # Import translation helper
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util
from packaging import version

from .ble import BoksBluetoothDevice
from .const import (
    CONF_ANONYMIZE_LOGS,
    CONF_CONFIG_KEY,
    DEFAULT_FULL_REFRESH_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_LOGS_RETRIEVED,
    TIMEOUT_BLE_CONNECTION,  # Import DOMAIN and defaults
)
from .errors import BoksError
from .logic.anonymizer import BoksAnonymizer
from .logic.log_processor import BoksLogProcessor
from .packets.base import BoksRXPacket
from .util import is_firmware_version_greater_than, process_device_info

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

    def set_translations(self, translations: dict[str, str]):
        """Set pre-loaded translations."""
        self._translations = translations

    def get_text(self, category: str, key: str, **kwargs) -> str:
        """Get a translated text from the pre-loaded cache. Defaults to key name."""
        # HA translation keys follow the pattern: component.<domain>.<category>.<key>
        # For 'exceptions', it's component.<domain>.exceptions.<key>.message
        full_key = f"component.{DOMAIN}.{category}.{key}"
        if category == "exceptions":
            full_key += ".message"

        text = self._translations.get(full_key, key)
        try:
            return text.format(**kwargs)
        except Exception as e:
            _LOGGER.warning("Failed to format translation %s: %s", full_key, e)
            return text

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

        # Fire event
        event_data = {
            "device_id": self.entry.entry_id,
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

    async def trigger_firmware_update_check(self, required_version: str) -> bool:
        """
        Trigger a firmware update check and download.

        Args:
            required_version: The minimum firmware version required (e.g., "4.3.3")

        Returns:
            bool: True if firmware was successfully downloaded, False otherwise
        """
        # Get the update entity for this coordinator
        update_entity = None
        update_component = self.hass.data.get("entity_components", {}).get("update")

        if update_component:
            for entity in update_component.entities:
                if entity.unique_id == f"{self.entry.entry_id}_firmware_update":
                    update_entity = entity
                    break

        if not update_entity:
            _LOGGER.error("Could not find firmware update entity")
            return False

        # Trigger the update check on the update entity
        return await update_entity.trigger_update_check(required_version)

    async def ensure_min_firmware_version(self, required_version: str, translation_key: str = "firmware_version_required", update_target_version: str = None) -> None:
        """
        Ensure the device firmware version is greater than required_version.
        If not, triggers an update check for update_target_version (defaults to required_version).
        Raises HomeAssistantError if requirements aren't met.

        Args:
            required_version: The version that the current firmware must be greater than.
            translation_key: The translation key for the error message if version is insufficient.
            update_target_version: The version to check for update against. Defaults to required_version.
        """
        if update_target_version is None:
            update_target_version = required_version

        software_revision = None
        if self.device_info:
            software_revision = self.device_info.get("sw_version")

        if software_revision:
            if not is_firmware_version_greater_than(software_revision, required_version):
                _LOGGER.warning("Firmware version %s is not greater than %s. Triggering update check for %s.", software_revision, required_version, update_target_version)

                update_triggered = await self.trigger_firmware_update_check(update_target_version)

                if not update_triggered:
                    raise HomeAssistantError(
                        translation_domain=DOMAIN,
                        translation_key="firmware_update_failed",
                        translation_placeholders={"version": update_target_version}
                    )

                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key=translation_key,
                    translation_placeholders={
                        "current_version": software_revision,
                        "required_version": required_version
                    }
                )
        else:
            _LOGGER.warning("Could not determine software revision to check against %s", required_version)

    async def async_ensure_prerequisites(self, feature_name: str, min_hw: str, min_sw: str) -> None:
        """
        Ensure hardware and software prerequisites are met.
        Raises HomeAssistantError if not.
        """
        hw_version = self.device_info.get("hw_version")
        sw_version = self.device_info.get("sw_version")

        # 1. Hardware Check
        if hw_version:
            try:
                if version.parse(hw_version) < version.parse(min_hw):
                    _LOGGER.error("Hardware version %s is insufficient for %s. Required: %s", hw_version, feature_name, min_hw)
                    raise BoksError(
                        "hardware_unsupported",
                        {
                            "feature": feature_name,
                            "required_hw": min_hw,
                            "current_hw": hw_version
                        }
                    )
            except (version.InvalidVersion, ValueError) as e:
                _LOGGER.warning("Error parsing HW version '%s': %s", hw_version, e)
        else:
             _LOGGER.warning("Could not determine HW version for %s prerequisites", feature_name)

        # 2. Software Check
        if sw_version:
            if not is_firmware_version_greater_than(sw_version, min_sw) and sw_version != min_sw:
                _LOGGER.error("Software version %s is insufficient for %s. Required: %s", sw_version, feature_name, min_sw)
                # Trigger update check
                await self.trigger_firmware_update_check(min_sw)

                raise BoksError(
                    "firmware_update_required",
                    {
                        "feature": feature_name,
                        "required_sw": min_sw,
                        "current_sw": sw_version
                    }
                )
        else:
             _LOGGER.warning("Could not determine SW version for %s prerequisites", feature_name)
