"""Update platform for Boks integration."""
import logging
import os
import tempfile
import aiohttp
import shutil
from typing import Any, Dict, Optional
from pathlib import Path

from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.components import persistent_notification
from homeassistant.helpers import translation

from .const import DOMAIN, FIRMWARE_MAPPING
from .entity import BoksEntity
from .coordinator import BoksDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: dict[str, Any],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Boks update entities."""
    coordinator: BoksDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BoksUpdateEntity(coordinator, entry)])


class BoksUpdateEntity(BoksEntity, UpdateEntity):
    """Representation of a Boks firmware update entity."""

    _attr_translation_key = "firmware_update"

    def __init__(self, coordinator: BoksDataUpdateCoordinator, entry) -> None:
        """Initialize the update entity."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_firmware_update"
        self._attr_supported_features = UpdateEntityFeature.INSTALL

        # Track if an update is available based on error trigger
        self._update_available = False
        self._target_version: Optional[str] = None
        self._firmware_path: Optional[str] = None

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass."""
        await super().async_added_to_hass()
        # Load translations
        try:
            self._translations = await translation.async_get_translations(
                self.hass, self.hass.config.language, "firmware_update", {DOMAIN}
            )
        except Exception as e:
            _LOGGER.warning(f"Failed to load firmware update translations: {e}")
            self._translations = {}

    def _(self, key: str, **kwargs) -> str:
        """Get translated string."""
        if not self._translations:
            return key

        translated = self._translations.get(f"component.{DOMAIN}.firmware_update.{key}", key)

        # Format with placeholders if provided
        if kwargs:
            try:
                translated = translated.format(**kwargs)
            except (KeyError, ValueError):
                pass

        return translated

    @property
    def installed_version(self) -> str | None:
        """Version currently installed."""
        device_info = self.coordinator.device_info
        if device_info:
            return device_info.get("sw_version")
        return None

    @property
    def latest_version(self) -> str | None:
        """Latest version available for install."""
        # Only show latest version if update has been triggered
        if not self._update_available:
            return None

        return self._target_version

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Entity is available if update has been triggered
        return self._update_available

    def _get_internal_firmware_revision(self) -> str | None:
        """Get the internal firmware revision from coordinator data."""
        # Get the internal firmware revision (e.g., "10/125")
        internal_revision = None
        if self.coordinator.data and "device_info_service" in self.coordinator.data:
            internal_revision = self.coordinator.data["device_info_service"].get("firmware_revision")

        return internal_revision

    async def async_install(
        self, version: str | None, backup: bool | None = False, **kwargs: Any
    ) -> None:
        """Install an update - in our case, just show a notification."""
        if not self._firmware_path or not self._target_version:
            _LOGGER.error("No firmware downloaded for installation")
            persistent_notification.async_create(
                self.hass,
                self._("no_firmware_downloaded"),
                self._("notification_title")
            )
            return

        # Create a user-accessible directory for the firmware (www folder)
        www_dir = Path(self.hass.config.path("www"))
        www_dir.mkdir(parents=True, exist_ok=True)

        # Move the firmware file to the accessible directory
        firmware_filename = f"boks_firmware_{self._target_version}.zip"
        accessible_path = www_dir / firmware_filename

        # URL for the user to access the file
        # /local/ maps to the www directory
        accessible_url = f"/local/{firmware_filename}"

        try:
            shutil.move(self._firmware_path, accessible_path)
            self._firmware_path = str(accessible_path)
        except Exception as e:
            _LOGGER.error(f"Failed to move firmware to accessible location: {e}")
            # If move fails, keep the original path
            pass

        # Notify user that firmware is ready with instructions
        persistent_notification.async_create(
            self.hass,
            self._("firmware_ready", version=self._target_version, file_path=self._firmware_path, download_url=accessible_url),
            self._("manual_action_required")
        )

        _LOGGER.info(self._("firmware_ready_info", version=self._target_version, file_path=self._firmware_path))

        # Reset update state
        self._update_available = False
        self._target_version = None
        self._firmware_path = None
        self.async_write_ha_state()

    async def trigger_update_check(self, required_version: str) -> bool:
        """
        Trigger an update check when an error occurs that requires a newer firmware.

        Args:
            required_version: The minimum firmware version required (e.g., "4.3.3")

        Returns:
            bool: True if firmware was successfully downloaded, False otherwise
        """
        # Get the internal firmware revision
        internal_revision = self._get_internal_firmware_revision()

        if not internal_revision:
            _LOGGER.error(self._("cannot_determine_revision"))
            return False

        # Check if we have mapping for this revision
        if internal_revision not in FIRMWARE_MAPPING:
            _LOGGER.error(self._("no_firmware_mapping", revision=internal_revision))
            return False

        # Find a suitable version (for now, we'll use the highest available version)
        available_versions = list(FIRMWARE_MAPPING[internal_revision].keys())
        if not available_versions:
            return False

        # Find the best matching version that meets the requirement
        # We want the lowest version that is >= required_version
        suitable_versions = [v for v in available_versions if self._is_version_higher_or_equal(v, required_version)]
        if not suitable_versions:
            _LOGGER.error(self._("no_suitable_version", version=required_version))
            return False

        # Select the lowest suitable version (closest to required_version)
        target_version = sorted(suitable_versions, key=lambda v: [int(i) for i in v.split('.')])[0]

        firmware_url = FIRMWARE_MAPPING[internal_revision][target_version]

        # Create a temporary file for the download
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, f"boks_firmware_{target_version}.zip")

        try:
            # Download the firmware
            session = async_get_clientsession(self.hass)
            async with session.get(firmware_url) as response:
                if response.status != 200:
                    _LOGGER.error(f"Failed to download firmware: HTTP {response.status}")
                    # Clean up temporary directory
                    shutil.rmtree(temp_dir, ignore_errors=True)

                    # Notify user about the download failure
                    persistent_notification.async_create(
                        self.hass,
                        self._("download_failed", version=target_version, status=response.status),
                        self._("download_failed_title")
                    )
                    return False

                # Write the firmware to the temporary file
                # Use aiofiles for async file operations
                try:
                    import aiofiles
                    async with aiofiles.open(temp_file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(1024):
                            await f.write(chunk)
                except ImportError:
                    # Fallback to sync operation if aiofiles is not available
                    # This should be avoided in production but kept for compatibility
                    def write_file_sync():
                        with open(temp_file_path, 'wb') as f:
                            for chunk in response.content.iter_chunked(1024):
                                f.write(chunk)
                    # Execute sync operation in thread pool to avoid blocking
                    await self.hass.async_add_executor_job(write_file_sync)

            # Store the firmware path and version
            self._firmware_path = temp_file_path
            self._target_version = target_version
            self._update_available = True

            # Update the entity state
            self.async_write_ha_state()

            _LOGGER.info(f"Firmware update {target_version} downloaded successfully to {temp_file_path}")
            return True

        except aiohttp.ClientError as e:
            _LOGGER.error(f"Network error during firmware download: {e}")
            # Clean up temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)

            # Notify user about the network error
            persistent_notification.async_create(
                self.hass,
                self._("network_error", version=target_version, error=str(e)),
                self._("network_error_title")
            )
            return False
        except Exception as e:
            _LOGGER.error(f"Error during firmware download: {e}")
            # Clean up temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)

            # Notify user about the error
            persistent_notification.async_create(
                self.hass,
                self._("generic_error", version=target_version, error=str(e)),
                self._("generic_error_title")
            )
            return False

    def _is_version_higher_or_equal(self, current_version: str, required_version: str) -> bool:
        """Check if current version is higher or equal to required version."""
        try:
            current_parts = [int(x) for x in current_version.split('.')]
            required_parts = [int(x) for x in required_version.split('.')]

            # Pad shorter version with zeros
            while len(current_parts) < len(required_parts):
                current_parts.append(0)
            while len(required_parts) < len(current_parts):
                required_parts.append(0)

            # Compare version parts
            for c, r in zip(current_parts, required_parts):
                if c > r:
                    return True
                if c < r:
                    return False
            return True  # Versions are equal
        except Exception:
            # If parsing fails, assume version is sufficient
            return True
