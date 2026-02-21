"""Commands Logic Controller for Boks."""
import logging
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from ..ble.const import BoksConfigType
from ..const import CONF_MASTER_CODE, DOMAIN
from ..errors import BoksError
from ..logic.anonymizer import BoksAnonymizer

if TYPE_CHECKING:
    from ..coordinator import BoksDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

class BoksCommandsController:
    """Controller for Command operations."""

    def __init__(self, hass: HomeAssistant, coordinator: "BoksDataUpdateCoordinator"):
        self.hass = hass
        self.coordinator = coordinator

    async def open_door(self, code: str | None = None) -> None:
        """Open the door."""
        code_str = code.strip().upper() if code else None

        _LOGGER.info("Open Door requested via service for %s",
                     BoksAnonymizer.anonymize_mac(self.coordinator.ble_device.address, self.coordinator.ble_device.anonymize_logs))

        # Try to find the lock entity to use its logic (and state update)
        lock_entity = None
        entity_registry = er.async_get(self.hass)
        entries = er.async_entries_for_config_entry(entity_registry, self.coordinator.entry.entry_id)
        for entry in entries:
            if entry.domain == "lock":
                component = self.hass.data.get("entity_components", {}).get("lock")
                if component:
                    lock_entity = component.get_entity(entry.entity_id)
                    break

        if lock_entity:
            # Delegate to entity
            await lock_entity.async_open(code=code_str)
            _LOGGER.info("Open Door service completed via entity")
        else:
            # Fallback: direct call if entity not found
            try:
                await self.coordinator.ble_device.connect()

                # Logic mirrored from lock.py
                if not code_str:
                    code_str = self.coordinator.entry.data.get(CONF_MASTER_CODE)

                if not code_str and self.coordinator.ble_device.config_key_str:
                    try:
                        code_str = await self.coordinator.ble_device.create_pin_code(code_type="single")
                    except Exception as e:
                        _LOGGER.warning("Fallback generation failed: %s", e)

                if not code_str:
                     raise BoksError("pin_code_invalid")

                await self.coordinator.ble_device.open_door(code=code_str)
            except Exception as e:
                 # Wrap device errors
                 _LOGGER.error("Direct open door failed: %s", e)
                 raise HomeAssistantError(f"Failed to open door: {e}") from e
            finally:
                await self.coordinator.ble_device.disconnect()

    async def sync_logs(self) -> None:
        """Sync logs."""
        _LOGGER.info("Manual log sync requested for %s",
                     BoksAnonymizer.anonymize_mac(self.coordinator.ble_device.address, self.coordinator.ble_device.anonymize_logs))
        try:
            await self.coordinator.async_sync_logs(update_state=True)
            _LOGGER.info("Manual log sync completed")
        except Exception as e:
            _LOGGER.error("Failed to sync logs: %s", e)
            raise HomeAssistantError(f"Failed to sync logs: {e}") from e

    async def set_configuration(self, laposte: bool | None = None) -> None:
        """Set configuration."""
        try:
            if laposte is not None:
                if laposte:
                    await self.coordinator.updates.ensure_prerequisites("La Poste", "4.0", "4.2.0")

                _LOGGER.info("Setting La Poste configuration to %s", laposte)
                await self.coordinator.ble_device.connect()
                try:
                    await self.coordinator.ble_device.set_configuration(BoksConfigType.SCAN_LAPOSTE_NFC_TAGS, laposte)
                finally:
                    await self.coordinator.ble_device.disconnect()
        except BoksError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=e.translation_key,
                translation_placeholders=e.translation_placeholders
            ) from e
        except Exception as e:
            _LOGGER.error("Error setting configuration: %s", e)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="unexpected_set_configuration_error",
                translation_placeholders={"error": str(e)}
            ) from e

    async def ask_door_status(self) -> dict:
        """Ask door status."""
        _LOGGER.info("Door status poll requested for %s",
                     BoksAnonymizer.anonymize_mac(self.coordinator.ble_device.address, self.coordinator.ble_device.anonymize_logs))

        try:
            await self.coordinator.ble_device.connect()
            is_open = await self.coordinator.ble_device.get_door_status()
            _LOGGER.info("Door status poll completed. Open: %s", is_open)
            return {"is_open": is_open}
        except Exception as e:
             _LOGGER.error("Error asking door status: %s", e)
             raise HomeAssistantError(f"Error asking door status: {e}") from e
        finally:
            await self.coordinator.ble_device.disconnect()
