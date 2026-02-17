"""Firmware update manager for Boks."""
import json
import logging
import os
import shutil
import uuid

import aiohttp
from homeassistant.core import HomeAssistant

from ..const import (
    BOKS_HARDWARE_INFO,
    TPL_DELETE_TOKEN,
    TPL_EXPECTED_HW,
    TPL_FW_FILENAME,
    TPL_INTERNAL_REV,
    TPL_NORDIC_LIB,
    TPL_STYLE,
    TPL_TARGET_VER,
    TPL_TRANSLATIONS,
    TPL_UPDATER,
    UPDATE_INDEX_FILENAME,
    UPDATE_JSON_FILENAME,
    UPDATE_WWW_DIR,
)

_LOGGER = logging.getLogger(__name__)

SECURE_DFU_LIB_URL = "https://unpkg.com/@thib3113/web-bluetooth-dfu/dist/secure-dfu.js"

class BoksUpdateManager:
    """Manages Boks firmware files and local update web interface."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the update manager."""
        self.hass = hass
        self.www_path = hass.config.path("www", UPDATE_WWW_DIR)
        self.json_path = os.path.join(self.www_path, UPDATE_JSON_FILENAME)
        self.assets_source_path = os.path.join(os.path.dirname(__file__), "assets")

    async def async_prepare_update(self, target_version: str, internal_revision: str) -> str:
        """
        Download firmware and prepare the local web environment.
        Returns the relative URL to the specific version flasher.
        """
        hw_info = BOKS_HARDWARE_INFO.get(internal_revision)
        if not hw_info or target_version not in hw_info["firmwares"]:
            raise ValueError(f"Version {target_version} not found for hardware {internal_revision}")

        firmware_url = hw_info["firmwares"][target_version]
        chipset = hw_info["chipset"]

        _LOGGER.info("Downloading Boks firmware v%s from %s", target_version, firmware_url)
        _LOGGER.info("Downloading SecureDFU library from %s", SECURE_DFU_LIB_URL)

        async with aiohttp.ClientSession() as session:
            # 1. Download Firmware
            async with session.get(firmware_url) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Failed to download firmware: {resp.status}")
                fw_content = await resp.read()

            # 2. Download SecureDFU Lib
            async with session.get(SECURE_DFU_LIB_URL) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Failed to download SecureDFU lib: {resp.status}")
                lib_content = await resp.text(encoding='utf-8')

        # 3. File operations (Offloaded to executor)
        await self.hass.async_add_executor_job(
            self._sync_files, target_version, internal_revision, chipset, fw_content, lib_content
        )

        return f"/local/{UPDATE_WWW_DIR}/v{target_version}/{UPDATE_INDEX_FILENAME}"

    async def async_delete_package(self, version: str) -> None:
        """Delete a specific update package."""
        await self.hass.async_add_executor_job(self._delete_package_sync, version)

    def _delete_package_sync(self, version: str) -> None:
        """Synchronously delete package files and update catalog."""
        version_dir = os.path.join(self.www_path, f"v{version}")

        # 1. Remove Directory
        if os.path.exists(version_dir):
            try:
                shutil.rmtree(version_dir)
                _LOGGER.info("Deleted update package for version %s", version)
            except Exception as e:
                _LOGGER.error("Failed to delete directory %s: %s", version_dir, e)
        else:
            _LOGGER.warning("Update package %s not found at %s", version, version_dir)

        # 2. Update Catalog
        self._remove_from_json_catalog(version)

    def _sync_files(self, version: str, internal_rev: str, chipset: str, fw_content: bytes, lib_content: str):
        """Perform all filesystem operations for a specific version."""
        # Ensure base directory exists
        os.makedirs(self.www_path, exist_ok=True)

        version_dir = os.path.join(self.www_path, f"v{version}")
        os.makedirs(version_dir, exist_ok=True)

        # Generate a unique delete token
        delete_token = uuid.uuid4().hex

        # 1. Write Firmware binary
        fw_filename = f"boks_{chipset}_{version}.zip"
        with open(os.path.join(version_dir, fw_filename), "wb") as f:
            f.write(fw_content)

        # 2. Generate the version-specific index.html (self-contained flasher)
        self._generate_version_index(version_dir, version, internal_rev, chipset, fw_filename, lib_content, delete_token)

        # 3. Update the root versions.json catalog
        self._update_json_catalog(version, internal_rev, str(chipset), delete_token)

        # 4. Copy/Update the root portal index.html
        self._copy_portal_index()

    def _generate_version_index(self, target_dir, version, internal_rev, chipset, fw_filename, lib_content, delete_token):
        """Generate a flasher HTML for a specific version using templates and assets."""
        def read_asset(name):
            with open(os.path.join(self.assets_source_path, name), encoding="utf-8") as f:
                return f.read()

        html_template = read_asset("update_template.html")

        # Inject styles and scripts
        final_html = html_template.replace(TPL_STYLE, read_asset("style.css"))

        # Inject the downloaded library instead of the local asset
        final_html = final_html.replace(TPL_NORDIC_LIB, lib_content)

        final_html = final_html.replace(TPL_TRANSLATIONS, read_asset("translations.js"))
        final_html = final_html.replace(TPL_UPDATER, read_asset("updater.js"))

        # Inject configuration values
        final_html = final_html.replace(TPL_TARGET_VER, version)
        final_html = final_html.replace(TPL_EXPECTED_HW, str(chipset))
        final_html = final_html.replace(TPL_INTERNAL_REV, internal_rev)
        final_html = final_html.replace(TPL_FW_FILENAME, fw_filename)
        final_html = final_html.replace(TPL_DELETE_TOKEN, delete_token)

        with open(os.path.join(target_dir, UPDATE_INDEX_FILENAME), "w", encoding="utf-8") as f:
            f.write(final_html)

    def _update_json_catalog(self, version: str, internal_rev: str, chipset: str, delete_token: str):
        """Update the JSON catalog with the new version info."""
        data = {"versions": {}}
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                _LOGGER.warning("Could not parse existing versions.json, recreating it")

        data["versions"][version] = {
            "chipset": chipset,
            "internal_rev": internal_rev,
            "path": f"v{version}/{UPDATE_INDEX_FILENAME}",
            "delete_token": delete_token
        }

        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _remove_from_json_catalog(self, version: str):
        """Remove a version from the JSON catalog."""
        if not os.path.exists(self.json_path):
            return

        try:
            with open(self.json_path, encoding="utf-8") as f:
                data = json.load(f)

            if version in data.get("versions", {}):
                del data["versions"][version]
                with open(self.json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                _LOGGER.debug("Removed version %s from catalog", version)
        except Exception as e:
            _LOGGER.warning("Failed to update versions.json: %s", e)

    def verify_token(self, version: str, token: str) -> bool:
        """Verify the delete token for a version."""
        if not os.path.exists(self.json_path):
            return False
        try:
            with open(self.json_path, encoding="utf-8") as f:
                data = json.load(f)

            stored_info = data.get("versions", {}).get(version)
            if stored_info and stored_info.get("delete_token") == token:
                return True
        except Exception:
            pass
        return False

    def _copy_portal_index(self):
        """Copy the portal.html asset to the root index.html."""
        src = os.path.join(self.assets_source_path, "portal.html")
        dst = os.path.join(self.www_path, UPDATE_INDEX_FILENAME)

        if not os.path.exists(src):
            _LOGGER.error("Portal template not found at %s", src)
            return

        shutil.copy2(src, dst)
        _LOGGER.debug("Boks update portal index.html synchronized")
