"""DataUpdateCoordinator for Boks."""

import asyncio
import logging
from datetime import timedelta, datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.components import bluetooth
from homeassistant.const import CONF_ADDRESS
from homeassistant.helpers import translation # Import translation helper

from .ble import BoksBluetoothDevice, BoksError
from .ble.log_entry import BoksLogEntry # Import BoksLogEntry
from .const import DOMAIN, CONF_CONFIG_KEY # Import DOMAIN

_LOGGER = logging.getLogger(__name__)

class BoksDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Boks data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize global Boks data updater."""
        self.ble_device = BoksBluetoothDevice(
            hass=hass,
            address=entry.data[CONF_ADDRESS],
            config_key=entry.data.get(CONF_CONFIG_KEY)
        )
        # Register callback for push updates (door status, battery info)
        self.ble_device.register_status_callback(self._handle_status_update)
        
        self.entry = entry
        _LOGGER.debug("BoksDataUpdateCoordinator initialized with Address: %s, Config Key Present: %s",
                       entry.data[CONF_ADDRESS], bool(entry.data.get(CONF_CONFIG_KEY)))
        self._last_battery_update = None
        self.full_refresh_interval_hours = entry.options.get("full_refresh_interval", 12)
        # Set the full refresh interval on the BLE device
        self.ble_device.set_full_refresh_interval(self.full_refresh_interval_hours)

        # Get scan interval from options, default to 1 minute
        scan_interval_minutes = entry.options.get("scan_interval", 1)
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

    def _handle_status_update(self, status_data: dict):
        """Handle push updates from the device."""
        if self.data is None:
            self.data = {}

        self.data.update(status_data)
        self.async_set_updated_data(self.data)


    async def async_sync_logs(self, update_state: bool = True) -> dict:
        """
        Fetch logs from the device.
        If update_state is True, it updates the coordinator data and notifies listeners.
        Returns a dict with 'latest_logs' and 'last_log_fetch_ts' if successful, else empty dict.
        """
        result = {}
        try:
            # Connect to increment reference counter
            await self.ble_device.connect()

            log_count = await self.ble_device.get_logs_count()
            if log_count > 0:
                _LOGGER.info(f"Found {log_count} logs. Downloading...")
                logs_from_device: List[BoksLogEntry] = await self.ble_device.get_logs(log_count)
                _LOGGER.debug(f"Raw logs response from device: {logs_from_device}")

                if logs_from_device:
                    _LOGGER.info(f"Retrieved {len(logs_from_device)} logs.")
                    # Filter out None log entries
                    valid_logs = [log for log in logs_from_device if log is not None]
                    if len(valid_logs) != len(logs_from_device):
                        _LOGGER.warning(f"Filtered out {len(logs_from_device) - len(valid_logs)} None log entries")

                    # Load translations once
                    # Use the helper function, not a method on hass
                    try:
                        # Attempt to fetch translations. Category None fetches all? Or we try 'state'.
                        # 'log_events' is custom, so it might be under a generic category or merged.
                        # Let's try without category (None) or fallback to empty dict if it fails.
                        translations = await translation.async_get_translations(self.hass, self.hass.config.language, "state", {DOMAIN})
                    except Exception as e:
                        _LOGGER.warning(f"Failed to load translations: {e}")
                        translations = {}

                    event_data = {
                        "device_id": self.entry.entry_id,
                        "address": self.entry.data[CONF_ADDRESS],
                        "logs": []
                    }

                    # Process logs with debug logging
                    for i, log in enumerate(valid_logs):
                        _LOGGER.debug(f"Processing log {i}: {log} (type: {type(log)})")
                        # Additional safety check for None log objects
                        if log is not None:
                            try:
                                # Construct the full translation key expected by HA
                                # Our keys in en.json/fr.json are now under "state": { "log_events": { ... } }
                                # This maps to component.boks.state.log_events.KEY
                                
                                # log.description is e.g. "log_events.code_ble_valid"
                                # So we just need to prepend component.boks.state.
                                
                                key = f"component.{DOMAIN}.state.{log.description}"
                                translated_description = translations.get(key, log.description)
                                
                                # If simple lookup failed, fallback to original behavior (key)
                                
                                log_entry = {
                                    "opcode": getattr(log, "opcode", "unknown"),
                                    "payload": getattr(log, "payload", b"").hex() if getattr(log, "payload", None) is not None else "",
                                    "timestamp": getattr(log, "timestamp", 0),
                                    "event_type": getattr(log, "event_type", "unknown"),
                                    "description": translated_description, # Use translated description
                                    **(getattr(log, "extra_data", {}) or {}),
                                }
                                event_data["logs"].append(log_entry)
                                _LOGGER.debug(f"Added log entry: {log_entry}")
                            except Exception as e:
                                _LOGGER.warning(f"Error processing log at index {i}: {e}")
                                _LOGGER.warning(f"Log object: {log}")
                        else:
                            _LOGGER.warning(f"Skipping None log at index {i}")
                    self.hass.bus.async_fire(f"{DOMAIN}_logs_retrieved", event_data)

                    result["latest_logs"] = event_data["logs"]
                    result["last_log_fetch_ts"] = datetime.now().isoformat()

                    if update_state:
                        if self.data is None:
                            self.data = {}
                        self.data.update(result)
                        self.async_set_updated_data(self.data)
            else:
                _LOGGER.debug("No logs to retrieve.")

        except Exception as e:
            _LOGGER.warning(f"Failed to sync logs: {e}")
        finally:
            # Always disconnect to decrement reference counter
            await self.ble_device.disconnect()

        return result

    async def _async_update_data(self) -> dict:
        """Fetch data from the Boks."""
        data = self.data if self.data else {} # Initialize data here
        try:
            # We do a quick connect-poll-disconnect cycle
            # Note: If the device is already connected via an active command,
            # the BoksBle class handles the lock.

            async with asyncio.timeout(30):
                # Always connect to increment reference counter
                # Try to get the BLEDevice from HA's cache (Best Practice)
                # First try with connectable=True, then with connectable=False
                ble_device_struct = bluetooth.async_ble_device_from_address(
                    self.hass, self.entry.data[CONF_ADDRESS], connectable=True
                )
                if not ble_device_struct:
                    # If not found with connectable=True, try with connectable=False
                    ble_device_struct = bluetooth.async_ble_device_from_address(
                        self.hass, self.entry.data[CONF_ADDRESS], connectable=False
                    )

                if ble_device_struct:
                    await self.ble_device.connect(device=ble_device_struct)
                else:
                    # If not in cache, try connecting anyway (might fail or use cached address in Bleak)
                    # But usually we need the BLEDevice object for Home Assistant
                    # If we can't find it, we can't connect reliably.
                    # However, BoksBle.connect() handles None device if address is known.
                    # But let's be strict here as per previous logic.
                    # Actually, previous logic raised UpdateFailed.
                    # Let's try to connect with just address if struct is missing,
                    # but BoksBle.connect() expects device or uses address.
                    # Let's stick to previous behavior: fail if not found.
                    raise UpdateFailed("device_not_in_cache")

                try:
                    now = datetime.now()

                    # Only fetch battery if we don't have it yet (first run)
                    # Afterwards, battery is updated only via door events (see device.py)
                    should_fetch_battery = "battery_level" not in data
                    
                    if should_fetch_battery:
                        _LOGGER.debug("Fetching battery level (Initial)...")
                        try:
                            battery_level = await self.ble_device.get_battery_level()
                            data["battery_level"] = battery_level
                            self._last_battery_update = now
                            _LOGGER.debug(f"Battery level fetched: {battery_level}")
                        except Exception as e:
                            _LOGGER.warning("Failed to fetch battery level: %s", e)
                        
                        # Fetch battery temperature
                        _LOGGER.debug("Fetching battery temperature...")
                        try:
                            battery_temperature = await self.ble_device.get_battery_temperature()
                            data["battery_temperature"] = battery_temperature
                            _LOGGER.debug(f"Battery temperature fetched: {battery_temperature}°C")
                        except Exception as e:
                            _LOGGER.warning("Failed to fetch battery temperature: %s", e)
                    else:
                        _LOGGER.debug("Battery fetch skipped (handled by door events).")

                    # 2. Get Code Counts (Always fetch as it doesn't require config key)
                    _LOGGER.debug("Fetching code counts...")
                    try:
                        counts = await self.ble_device.get_code_counts()
                        data.update(counts)
                        _LOGGER.debug(f"Code counts fetched: {counts}")
                    except BoksError as e:
                        _LOGGER.warning("Could not fetch code counts: %s", e)

                    # 4. Get Device Information (Always update on poll, or maybe throttle?)
                    # Since these don't change often, we could throttle, but for now let's fetch to ensure we have them.
                    # Actually, reading 7 characteristics every poll might be too much.
                    # Let's only fetch if we don't have them or if it's been a while (e.g. 24h).
                    should_fetch_device_info = True
                    if "device_info_service" in data:
                         # If we have data, maybe skip? But user might update firmware.
                         # Let's throttle to once every 24h (or 2x full refresh interval)
                         last_fetch = data.get("last_device_info_fetch")
                         if last_fetch:
                             last_fetch_dt = datetime.fromisoformat(last_fetch)
                             # Device info changes rarely, so we use 2x the normal refresh interval
                             device_info_interval_hours = self.full_refresh_interval_hours * 2
                             if (now - last_fetch_dt) < timedelta(hours=device_info_interval_hours):
                                 should_fetch_device_info = False
                                 _LOGGER.debug(f"Skipping device info update (last update < {device_info_interval_hours}h ago)")

                    if should_fetch_device_info:
                        _LOGGER.debug("Fetching device information...")
                        try:
                            device_info = await self.ble_device.get_device_information()
                            data["device_info_service"] = device_info
                            data["last_device_info_fetch"] = now.isoformat()

                            # Update device registry
                            device_registry = dr.async_get(self.hass)
                            device_entry = device_registry.async_get_device(
                                identifiers={(DOMAIN, self.entry.data[CONF_ADDRESS])},
                            )

                            if device_entry:
                                update_kwargs = {}
                                if device_info.get("software_revision"):
                                    update_kwargs["sw_version"] = device_info["software_revision"]
                                if device_info.get("hardware_revision"):
                                    update_kwargs["hw_version"] = device_info["hardware_revision"]
                                if device_info.get("manufacturer_name"):
                                    update_kwargs["manufacturer"] = device_info["manufacturer_name"]
                                if device_info.get("model_number"):
                                    update_kwargs["model"] = device_info["model_number"]

                                if update_kwargs:
                                    device_registry.async_update_device(
                                        device_entry.id, **update_kwargs
                                    )
                                    _LOGGER.info("Device registry updated with new info: %s", update_kwargs)

                        except Exception as e:
                            _LOGGER.warning("Failed to fetch device information: %s", e)

                    # 5. Auto-download logs
                    logs_data = await self.async_sync_logs(update_state=False)
                    if logs_data:
                        data.update(logs_data)

                finally:
                    # Disconnect after update to save battery and avoid blue LED
                    # This will decrement the reference counter
                    await self.ble_device.disconnect()

        except asyncio.TimeoutError:
            _LOGGER.error("Timeout during Boks BLE data update")
            # If the device timed out, we might be disconnected.
            # We don't raise UpdateFailed here immediately to allow other parts to work.
            # The next update cycle will try to reconnect.
        except UpdateFailed:
            # Re-raise pre-handled failures (like Device not found) without extra logging
            raise
        except Exception as err:
            # If we fail completely (cannot connect), we keep old data if available
            if self.data:
                _LOGGER.warning(f"Update failed, keeping old data: {err}")
                return self.data
            raise UpdateFailed(f"Error communicating with Boks: {err}") from err

        return data
