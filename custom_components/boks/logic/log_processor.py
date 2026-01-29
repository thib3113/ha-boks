"""Log processing and enrichment for Boks."""
import logging
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from ..const import DOMAIN
from ..packets.base import BoksRXPacket

_LOGGER = logging.getLogger(__name__)

class BoksLogProcessor:
    """Class to handle log enrichment, translation and HA registry updates."""

    def __init__(self, hass: HomeAssistant, address: str):
        """Initialize the processor."""
        self.hass = hass
        self.address = address

    async def async_enrich_log_entry(self, log: BoksRXPacket | dict, translations: dict[str, str]) -> dict:
        """Enrich a log entry with translations, tag names and formatting."""
        # Extract basic info
        event_type = getattr(log, "event_type", "unknown") if not isinstance(log, dict) else log.get("event_type", "unknown")
        opcode = getattr(log, "opcode", "unknown") if not isinstance(log, dict) else log.get("opcode", "unknown")
        payload = getattr(log, "payload", b"") if not isinstance(log, dict) else log.get("payload", "")
        timestamp = getattr(log, "timestamp", 0) if not isinstance(log, dict) else log.get("timestamp", 0)
        extra_data = (getattr(log, "extra_data", {}) or {}).copy() if not isinstance(log, dict) else (log.get("extra_data", {}) or {}).copy()

        # 1. Base Translation
        translated_description = self._translate_base_description(event_type, translations)

        # 2. Enrich with Diagnostic Errors
        translated_description = self._enrich_diagnostic_error(event_type, extra_data, translations, translated_description)

        # 3. Enrich with Power Off Reasons
        translated_description = self._enrich_power_off_reason(event_type, extra_data, translations, translated_description)

        # 4. Enrich with Tag Type Description
        self._enrich_tag_type(extra_data, translations)

        # 5. Enrich with NFC Tag Name from HA Registry
        tag_name = await self._resolve_tag_name(extra_data)
        if tag_name:
            extra_data["tag_name"] = tag_name

        # 6. Update last_scanned if needed
        await self._update_tag_last_scanned(event_type, timestamp, extra_data)

        return {
            "opcode": opcode,
            "payload": payload.hex() if isinstance(payload, (bytes, bytearray)) else payload,
            "timestamp": timestamp,
            "event_type": event_type,
            "description": translated_description,
            "extra_data": extra_data,
        }

    @staticmethod
    def _translate_base_description(event_type: str, translations: dict[str, str]) -> str:
        """Get the base translated description for an event type."""
        key = f"component.{DOMAIN}.entity.sensor.last_event.state.{event_type}"
        return translations.get(key, event_type)

    @staticmethod
    def _enrich_diagnostic_error(event_type: str, extra_data: dict, translations: dict[str, str], current_desc: str) -> str:
        """Enrich description with diagnostic error details."""
        if event_type == "error" and "error_description" in extra_data:
            diag_key = extra_data["error_description"]
            diag_full_key = f"component.{DOMAIN}.entity.sensor.last_event.state.{diag_key}"
            translated_diag = translations.get(diag_full_key, diag_key)
            if translated_diag != diag_key:
                extra_data["error_description"] = translated_diag
                return f"{current_desc}: {translated_diag}"
        return current_desc

    @staticmethod
    def _enrich_power_off_reason(event_type: str, extra_data: dict, translations: dict[str, str], current_desc: str) -> str:
        """Enrich description with power off reason."""
        if event_type == "power_off" and "reason_code" in extra_data:
            reason_code = extra_data["reason_code"]
            reason_key = f"component.{DOMAIN}.entity.sensor.last_event.state.power_off_reason_{reason_code}"
            translated_reason = translations.get(reason_key)
            if translated_reason:
                extra_data["reason_text"] = translated_reason
                return f"{current_desc}: {translated_reason}"
        return current_desc

    @staticmethod
    def _enrich_tag_type(extra_data: dict, translations: dict[str, str]) -> None:
        """Add human-readable tag type description."""
        tag_type = extra_data.get("tag_type")
        if tag_type:
            type_key = f"component.{DOMAIN}.entity.sensor.last_event.state.nfc_tag_type_{tag_type}"
            extra_data["tag_type_description"] = translations.get(type_key, f"Type {tag_type}")

    def _get_tags_collection(self):
        """Retrieve the tags collection helper robustly."""
        if "tag" not in self.hass.data:
            return None

        tag_manager = self.hass.data["tag"]

        # Case 1: Standard structure hass.data['tag']['tags']
        if isinstance(tag_manager, dict) and "tags" in tag_manager:
            return tag_manager["tags"]

        # Case 2: Direct collection object (observed in some environments)
        if hasattr(tag_manager, "data"):
             return tag_manager

        return None

    async def _resolve_tag_name(self, extra_data: dict) -> str | None:
        """Look up tag name in HA Registry (Tags and Entity Registry)."""
        tag_uid = extra_data.get("tag_uid")
        tag_name = extra_data.get("tag_name")

        if not tag_uid or tag_name:
            return tag_name

        try:
            # Normalize ID: uppercase and remove any non-hex chars
            import re
            tag_id_lookup = re.sub(r'[^0-9A-F]', '', tag_uid.upper())

            _LOGGER.debug("Resolving tag name for UID: %s (Normalized: %s)", tag_uid, tag_id_lookup)

            # 1. Try Tag Registry (Standard)
            tags_helper = self._get_tags_collection()
            if tags_helper and hasattr(tags_helper, "data") and tag_id_lookup in tags_helper.data:
                resolved_tag_info = tags_helper.data[tag_id_lookup]
                name = resolved_tag_info.get("name")
                if name:
                    _LOGGER.debug("Resolved tag name from Tag Registry: %s", name)
                    return name

            # 2. Try Entity Registry (Fallback for tags managed as entities)
            try:
                from homeassistant.helpers import entity_registry as er
                ent_reg = er.async_get(self.hass)
                # Find entities belonging to 'tag' platform with matching unique_id
                for entry in ent_reg.entities.values():
                    if entry.platform == "tag" and entry.unique_id == tag_id_lookup:
                        # Only return 'name' (user set). Ignore 'original_name' (usually "Tag <ID>")
                        if entry.name:
                            _LOGGER.debug("Resolved tag name from Entity Registry: %s", entry.name)
                            return entry.name
            except Exception as e:
                _LOGGER.debug("Failed to lookup in entity registry: %s", e)

            # 3. Last Resort Fallback: UID
            _LOGGER.debug("No custom tag name found for %s. Using UID.", tag_id_lookup)
            return tag_uid

        except Exception as e:
            _LOGGER.debug("Failed to lookup tag name for %s: %s", tag_uid, e)

        return tag_uid

    async def _update_tag_last_scanned(self, event_type: str, timestamp: int, extra_data: dict) -> None:
        """Update last_scanned attribute in HA tag registry."""
        tag_uid = extra_data.get("tag_uid")
        if event_type != "nfc_opening" or not tag_uid or "tag" not in self.hass.data:
            return

        try:
            tag_id_lookup = tag_uid.replace(":", "").upper()
            tags_helper = self._get_tags_collection()

            if not (tags_helper and tag_id_lookup in tags_helper.data):
                return

            last_scanned_dt = dt_util.utc_from_timestamp(timestamp)
            current_info = tags_helper.data[tag_id_lookup]

            if self._should_update_last_scanned(current_info.get("last_scanned"), last_scanned_dt):
                await tags_helper.async_update_item(tag_id_lookup, {"last_scanned": last_scanned_dt})
        except Exception as e:
            _LOGGER.debug("Failed to update scan date for %s: %s", tag_uid, e)

    @staticmethod
    def _should_update_last_scanned(current_last_scanned: Any, new_last_scanned: datetime) -> bool:
        """Determine if the last_scanned date should be updated."""
        if not current_last_scanned:
            return True

        current_dt = (dt_util.parse_datetime(current_last_scanned)
                    if isinstance(current_last_scanned, str)
                    else current_last_scanned)

        return bool(not current_dt or current_dt < new_last_scanned)
