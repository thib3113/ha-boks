"""Diagnostics support for Boks."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_ADDRESS
from homeassistant.components import bluetooth

from .const import DOMAIN, CONF_CONFIG_KEY, CONF_MASTER_CODE, CONF_MASTER_KEY
from .logic.anonymizer import BoksAnonymizer

TO_REDACT = {
    CONF_CONFIG_KEY,
    CONF_MASTER_KEY,
    CONF_MASTER_CODE,
    "credential",
    "password",
    "username",
    "serial_number",
    "address",
    "mac"
}

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Get BLE Device info
    # Try with connectable=True first, then connectable=False
    ble_device = bluetooth.async_ble_device_from_address(
        hass, entry.data[CONF_ADDRESS], connectable=True
    )
    if not ble_device:
        # If not found with connectable=True, try with connectable=False
        ble_device = bluetooth.async_ble_device_from_address(
            hass, entry.data[CONF_ADDRESS], connectable=False
        )

    ble_info = {}
    if ble_device:
        # Use our robust formatter for main scanner info
        scanner_summary = BoksAnonymizer.format_scanner_info(ble_device, anonymize=False)
        
        # Fallback details only for very low-level debugging in JSON
        raw_details = getattr(ble_device, "details", {})
        if not isinstance(raw_details, dict):
            raw_details = {"raw_value": str(raw_details)}

        ble_info = {
            "name": getattr(ble_device, "name", None),
            "address": getattr(ble_device, "address", None),
            "rssi": getattr(ble_device, "rssi", None),
            "scanner_summary": scanner_summary,
            "details": raw_details,
            "type": str(type(ble_device)),
        }

        # Try to extract manufacturer data if available
        if hasattr(ble_device, "metadata") and ble_device.metadata:
            # Safely access metadata attributes
            metadata = ble_device.metadata
            manufacturer_data = {}
            service_data = {}
            service_uuids = []

            if hasattr(metadata, "get"):
                manufacturer_data_dict = metadata.get("manufacturer_data", {})
                if isinstance(manufacturer_data_dict, dict):
                    manufacturer_data = {k: v.hex() for k, v in manufacturer_data_dict.items()}

                service_data_dict = metadata.get("service_data", {})
                if isinstance(service_data_dict, dict):
                    service_data = {k: v.hex() for k, v in service_data_dict.items()}

                service_uuids = metadata.get("uuids", [])

            ble_info["metadata"] = {
                "manufacturer_data": manufacturer_data,
                "service_uuids": service_uuids,
                "service_data": service_data
            }

    diagnostics_data = {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "coordinator_data": coordinator.data,
        "ble_device_info": ble_info,
        "device_info_service": coordinator.data.get("device_info_service") if coordinator.data else None,
    }

    return async_redact_data(diagnostics_data, TO_REDACT)
