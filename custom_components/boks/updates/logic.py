"""Update logic for Boks integration."""
import logging
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.network import get_url
from packaging import version

from .manager import BoksUpdateManager
from ..const import BOKS_HARDWARE_INFO, DOMAIN, UPDATE_NOTIFICATION_ID_PREFIX
from ..errors import BoksError

if TYPE_CHECKING:
    from ..coordinator import BoksDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

class BoksUpdateController:
    """Controller for Boks updates logic."""

    def __init__(self, hass: HomeAssistant, coordinator: "BoksDataUpdateCoordinator"):
        """Initialize the update controller."""
        self.hass = hass
        self.coordinator = coordinator

    async def ensure_prerequisites(self, feature_name: str, min_hw: str, min_sw: str) -> None:
        """
        Ensure hardware and software prerequisites are met.
        Triggers update package generation automatically if SW is too old.
        """
        # Retrieve robust device info (Cache -> Live -> Fallback)
        device_info = await self.coordinator.get_or_fetch_device_info()
        
        hw_version = device_info.get("hw_version")
        sw_version = device_info.get("sw_version")

        # 1. Hardware Check
        if hw_version:
            try:
                # Check if the hw_version is known in BOKS_HARDWARE_INFO
                known_hw_versions = [info["hw_version"] for info in BOKS_HARDWARE_INFO.values()]
                if hw_version not in known_hw_versions:
                        _LOGGER.warning("Unknown hardware version %s. Prerequisites check might be inaccurate.", hw_version)

                if version.parse(hw_version) < version.parse(min_hw):
                    _LOGGER.error("Hardware version %s is insufficient for %s. Required: %s", hw_version, feature_name, min_hw)
                    raise HomeAssistantError(
                        translation_domain=DOMAIN,
                        translation_key="hardware_unsupported",
                        translation_placeholders={
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
            def is_fw_ok(current, required):
                try:
                    return version.parse(current) >= version.parse(required)
                except Exception:
                    return False

            if not is_fw_ok(sw_version, min_sw):
                _LOGGER.warning("Software version %s is insufficient for %s. Required: %s. Generating update package...", sw_version, feature_name, min_sw)
                
                # Automatically trigger the update package generation
                self.hass.async_create_task(
                    self.generate_package(min_sw)
                )

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

    async def generate_package(self, target_version: str) -> None:
        """
        Process the update package generation logic.
        Uses coordinator to get internal revision.
        """
        device_info = await self.coordinator.get_or_fetch_device_info()
        internal_revision = device_info.get("internal_revision")
        current_version = device_info.get("sw_version")

        if not internal_revision:
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key="fw_hw_rev_unknown"
                )

        # Version Downgrade Protection
        if current_version:
            try:
                if version.parse(target_version) < version.parse(current_version):
                    raise HomeAssistantError(
                        translation_domain=DOMAIN,
                        translation_key="fw_downgrade_blocked",
                        translation_placeholders={
                            "target_version": target_version,
                            "current_version": current_version
                        }
                    )
            except (version.InvalidVersion, ValueError) as e:
                _LOGGER.warning("Error comparing versions: %s", e)

        # Prepare Update Package via Manager
        manager = BoksUpdateManager(self.hass)
        try:
            full_url_relative = await manager.async_prepare_update(target_version, internal_revision)
        except Exception as e:
            _LOGGER.error("Failed to prepare update package: %s", e)
            raise HomeAssistantError(f"Update package generation failed: {e}") from e

        # Notify
        base_url = get_url(self.hass)
        full_url = f"{base_url}{full_url_relative}"

        msg = self.coordinator.get_text("exceptions", "fw_update_package_ready_msg", target_version=target_version, url=full_url)
        title = self.coordinator.get_text("exceptions", "fw_update_package_ready_title", target_version=target_version)

        await self.hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "message": msg,
                "title": title,
                "notification_id": f"{UPDATE_NOTIFICATION_ID_PREFIX}{target_version}"
            }
        )