"""NFC Logic Controller for Boks."""
import asyncio
import logging
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant

from ..ble.const import BoksNotificationOpcode
from ..const import TIMEOUT_NFC_WAIT_RESULT
from ..errors import BoksError

if TYPE_CHECKING:
    from ..coordinator import BoksDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

class BoksNfcController:
    """Controller for NFC operations."""

    def __init__(self, hass: HomeAssistant, coordinator: "BoksDataUpdateCoordinator"):
        self.hass = hass
        self.coordinator = coordinator

    async def start_scan(self) -> None:
        """
        Start an NFC scan session.
        Initializes connection and sends command synchronously to catch errors early.
        Then spawns a background task to wait for the tag result.
        """
        # Prerequisites
        await self.coordinator.updates.ensure_prerequisites("NFC", "4.0", "4.3.3")

        # 1. Synchronous Phase: Connection & Start Command
        # This allows raising errors to the UI if auth fails or device is unreachable
        _LOGGER.info("Starting NFC scan session (Sync phase)...")
        await self.coordinator.ble_device.connect()
        try:
            success = await self.coordinator.ble_device.nfc_scan_start()
            if not success:
                # Should normally raise BoksError inside nfc_scan_start, but just in case
                raise BoksError("unknown")
        except Exception:
            # Ensure we disconnect if start fails synchronously
            await self.coordinator.ble_device.disconnect()
            raise

        # Notify user that scan is active (Command sent successfully)
        await self.hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "message": self.coordinator.get_text("common", "nfc_scan_started_msg"),
                "title": self.coordinator.get_text("common", "nfc_scan_started_title"),
                "notification_id": f"boks_nfc_scan_{self.coordinator.entry.entry_id}"
            }
        )

        _LOGGER.info("NFC scan started, spawning background listener...")

        # 2. Asynchronous Phase: Waiting for result
        self.hass.async_create_task(self._wait_for_scan_result())

    async def _wait_for_scan_result(self):
        """Background task waiting for the NFC tag notification."""
        scan_done = asyncio.Event()

        def scan_callback(data):
            # 0xC5 (Found), 0xC6 (Already exists), 0xC7 (Timeout)
            if data[0] in (0xC5, 0xC6, 0xC7):
                _LOGGER.debug("NFC Scan result received: 0x%02X", data[0])
                scan_done.set()

        self.coordinator.ble_device.register_opcode_callback(BoksNotificationOpcode.NOTIFY_NFC_TAG_FOUND, scan_callback)
        self.coordinator.ble_device.register_opcode_callback(BoksNotificationOpcode.ERROR_NFC_TAG_ALREADY_EXISTS_SCAN, scan_callback)
        self.coordinator.ble_device.register_opcode_callback(BoksNotificationOpcode.ERROR_NFC_TIMEOUT, scan_callback)

        try:
            await asyncio.wait_for(scan_done.wait(), timeout=TIMEOUT_NFC_WAIT_RESULT)
        except TimeoutError:
            _LOGGER.warning("NFC scan session timed out (no response from device).")
        except Exception as e:
            _LOGGER.error("Error in NFC background listener: %s", e)
        finally:
            self.coordinator.ble_device.unregister_opcode_callback(BoksNotificationOpcode.NOTIFY_NFC_TAG_FOUND, scan_callback)
            self.coordinator.ble_device.unregister_opcode_callback(BoksNotificationOpcode.ERROR_NFC_TAG_ALREADY_EXISTS_SCAN, scan_callback)
            self.coordinator.ble_device.unregister_opcode_callback(BoksNotificationOpcode.ERROR_NFC_TIMEOUT, scan_callback)

            # Always disconnect at the end of the session
            await self.coordinator.ble_device.disconnect()

    async def register_tag(self, uid: str, name: str | None) -> None:
        """Register a tag."""
        await self.coordinator.updates.ensure_prerequisites("NFC", "4.0", "4.3.3")
        await self.coordinator.ble_device.connect()
        try:
            await self.coordinator.ble_device.register_nfc_tag(uid, name)
        finally:
            await self.coordinator.ble_device.disconnect()

    async def unregister_tag(self, uid: str) -> None:
        """Unregister a tag."""
        await self.coordinator.updates.ensure_prerequisites("NFC", "4.0", "4.3.3")
        await self.coordinator.ble_device.connect()
        try:
            await self.coordinator.ble_device.unregister_nfc_tag(uid)
        finally:
            await self.coordinator.ble_device.disconnect()
