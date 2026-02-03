"""Codes Logic Controller for Boks."""
import asyncio
import logging
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from ..const import DOMAIN, MAX_MASTER_CODE_CLEAN_RANGE
from ..errors import BoksError

if TYPE_CHECKING:
    from ..coordinator import BoksDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

class BoksCodesController:
    """Controller for Code operations."""

    def __init__(self, hass: HomeAssistant, coordinator: "BoksDataUpdateCoordinator"):
        self.hass = hass
        self.coordinator = coordinator

    async def create_code(self, code: str, code_type: str, index: int = 0) -> dict:
        """Create a PIN code."""
        code = code.strip().upper()
        masked_code = "***" + code[-2:] if len(code) > 2 else "***"
        _LOGGER.info("Adding PIN Code: Code=%s, Type=%s, Index=%d", masked_code, code_type, index)

        try:
            await self.coordinator.ble_device.connect()
            created_code = await self.coordinator.ble_device.create_pin_code(code, code_type, index)
            _LOGGER.info("Code %s (%s) added successfully.", created_code, code_type)
            await self.coordinator.async_request_refresh()
            return {"code": created_code}
        except BoksError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=e.translation_key,
                translation_placeholders=e.translation_placeholders
            ) from e
        except Exception as e:
            _LOGGER.error("Error creating code: %s", e)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="unexpected_create_code_error",
                translation_placeholders={"error": str(e)}
            ) from e
        finally:
            await asyncio.shield(self.coordinator.ble_device.disconnect())

    async def delete_code(self, code_type: str, identifier: str | int) -> None:
        """Delete a PIN code."""
        if isinstance(identifier, str):
            identifier = identifier.strip().upper()

        _LOGGER.info("Deleting PIN Code: Identifier=%s, Type=%s", identifier, code_type)

        try:
            await self.coordinator.ble_device.connect()
            success = await self.coordinator.ble_device.delete_pin_code(code_type, identifier)
            if not success:
                 raise BoksError("delete_code_failed")

            _LOGGER.info("Code %s (%s) deleted successfully.", identifier, code_type)
            await self.coordinator.async_request_refresh()
        except BoksError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=e.translation_key,
                translation_placeholders=e.translation_placeholders
            ) from e
        except Exception as e:
            _LOGGER.error("Error deleting code: %s", e)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="unexpected_delete_code_error",
                translation_placeholders={"error": str(e)}
            ) from e
        finally:
            await asyncio.shield(self.coordinator.ble_device.disconnect())

    async def clean_master_codes(self, start_index: int, range_val: int) -> None:
        """Clean master codes in background."""
        if range_val > MAX_MASTER_CODE_CLEAN_RANGE:
            _LOGGER.warning("Requested range %d exceeds limit. Capping at %d.", range_val, MAX_MASTER_CODE_CLEAN_RANGE)
            range_val = MAX_MASTER_CODE_CLEAN_RANGE

        current_status = getattr(self.coordinator, "maintenance_status", {})
        if current_status.get("running", False):
            _LOGGER.warning("Clean Master Codes requested but a maintenance task is already running.")
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="maintenance_already_running"
            )

        _LOGGER.info("Clean Master Codes requested: Start=%d, Range=%d", start_index, range_val)

        async def _background_clean():
            total_to_clean = range_val
            current_idx = start_index
            self.coordinator.set_maintenance_status(
                running=True,
                current_index=current_idx,
                total_to_clean=total_to_clean
            )

            cleaned_count = 0

            try:
                if not self.coordinator.ble_device.is_connected:
                    await self.coordinator.ble_device.connect()

                for i in range(range_val):
                    target_index = start_index + i
                    self.coordinator.set_maintenance_status(
                        running=True,
                        current_index=i + 1,
                        total_to_clean=total_to_clean,
                        cleaned_count=cleaned_count
                    )

                    retry_count = 0
                    max_retries = 3
                    success = False

                    while retry_count < max_retries and not success:
                        try:
                            if not self.coordinator.ble_device.is_connected:
                                _LOGGER.debug("Reconnecting for index %d...", target_index)
                                await self.coordinator.ble_device.connect()

                            await self.coordinator.ble_device.delete_pin_code(type="master", index_or_code=target_index)
                            cleaned_count += 1
                            await asyncio.sleep(0.2)
                            success = True

                        except Exception as e:
                            retry_count += 1
                            _LOGGER.warning("Error cleaning index %d (Attempt %d/%d): %s", target_index, retry_count, max_retries, e)
                            await asyncio.sleep(1.0)

                    if not success:
                        _LOGGER.error("Failed to clean index %d after %d attempts. Aborting.", target_index, max_retries)
                        raise BoksError("connection_failed")

                self.coordinator.set_maintenance_status(
                    running=False,
                    current_index=total_to_clean,
                    total_to_clean=total_to_clean,
                    cleaned_count=cleaned_count
                )

                await self.hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "message": self.coordinator.get_text("common", "maintenance_success_msg", range=range_val, start_index=start_index),
                        "title": self.coordinator.get_text("common", "maintenance_success_title"),
                        "notification_id": f"boks_maintenance_{self.coordinator.entry.entry_id}"
                    }
                )

            except Exception as e:
                _LOGGER.error("Maintenance task failed: %s", e)
                self.coordinator.set_maintenance_status(running=False, error=str(e))

                await self.hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "message": self.coordinator.get_text("exceptions", "maintenance_error_msg", current_idx=current_idx, error=str(e)),
                        "title": self.coordinator.get_text("exceptions", "maintenance_error_title"),
                        "notification_id": f"boks_maintenance_{self.coordinator.entry.entry_id}"
                    }
                )

            finally:
                 await asyncio.shield(self.coordinator.ble_device.disconnect())
                 await asyncio.sleep(60)
                 self.coordinator.set_maintenance_status(running=False)

        self.hass.async_create_task(_background_clean())
