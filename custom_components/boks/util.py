"""Utility functions for Boks integration."""
from typing import Any

from homeassistant.const import CONF_ADDRESS, CONF_NAME
from packaging import version

from .const import BOKS_HARDWARE_INFO, DOMAIN


def infer_pcb_version(internal_revision: str) -> str | None:
    """Infer PCB version based on internal firmware revision."""
    if internal_revision in BOKS_HARDWARE_INFO:
        return BOKS_HARDWARE_INFO[internal_revision]["hw_version"]

    if internal_revision:
        return f"Unknown ({internal_revision})"

    return None

def process_device_info(entry_data: dict, device_info_service: dict = None) -> dict[str, Any]:
    """
    Process raw device info into a format suitable for HA Device Registry.

    Args:
        entry_data: The config entry data (containing address, name, etc.)
        device_info_service: The raw dictionary returned by BLE get_device_information()
                             Keys: software_revision, firmware_revision, hardware_revision,
                                   manufacturer_name, model_number

    Returns:
        A dictionary matching the DeviceInfo structure.
    """
    # Base info from Config Entry
    info = {
        "identifiers": {(DOMAIN, entry_data[CONF_ADDRESS])},
        "name": entry_data.get(CONF_NAME) or f"Boks {entry_data[CONF_ADDRESS]}",
        "manufacturer": "Boks",
        "model": "Boks ONE",
    }

    # If we have live data from the device, enrich the info
    if device_info_service:
        # 1. Software Version (e.g. 4.3.3)
        software_revision = device_info_service.get("software_revision")
        if software_revision:
            info["sw_version"] = software_revision

        # 2. Hardware Version (PCB Inference)
        # We prioritize our inference based on internal firmware revision (e.g. 10/125 -> PCB 4.0)
        internal_revision = device_info_service.get("firmware_revision")
        pcb_version = infer_pcb_version(internal_revision)

        if pcb_version:
            info["hw_version"] = pcb_version
        elif "hardware_revision" in device_info_service:
            # Fallback to reported HW revision if inference fails or no internal revision
            info["hw_version"] = device_info_service["hardware_revision"]

        # 3. Manufacturer
        if "manufacturer_name" in device_info_service:
            info["manufacturer"] = device_info_service["manufacturer_name"]

        # 4. Model
        # We stick to "Boks ONE" by default, but append the specific model if different
        # detected_model = device_info_service.get("model_number")
        # if detected_model and detected_model != "Boks ONE":
        #    info["model"] = f"Boks ONE ({detected_model})"
        # User requested to ignore model '2.0' for now, so we keep it simple.

    return info

def is_firmware_version_greater_than(current_version: str, required_version: str) -> bool:
    """
    Check if the current firmware version is greater than the required version.

    Args:
        current_version: Current firmware version string (e.g., "4.3.3")
        required_version: Required firmware version string (e.g., "4.3.3")

    Returns:
        bool: True if current version is greater than required version, False otherwise
    """
    try:
        return version.parse(current_version) > version.parse(required_version)
    except Exception:
        # If parsing fails, assume version is not sufficient
        return False
