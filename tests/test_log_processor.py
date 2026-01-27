"""Tests for the Boks log processor."""
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.boks.const import DOMAIN
from custom_components.boks.logic.log_processor import BoksLogProcessor
from custom_components.boks.ble.log_entry import BoksLogEntry
from custom_components.boks.ble.const import BoksHistoryEvent

@pytest.fixture
def log_processor(hass):
    """Fixture for BoksLogProcessor."""
    return BoksLogProcessor(hass, "AA:BB:CC:DD:EE:FF")

@pytest.fixture
def mock_translations():
    """Mock translations dictionary."""
    return {
        f"component.{DOMAIN}.entity.sensor.last_event.state.nfc_opening": "NFC Opening",
        f"component.{DOMAIN}.entity.sensor.last_event.state.error": "Error",
        f"component.{DOMAIN}.entity.sensor.last_event.state.power_off": "Power Off",
        f"component.{DOMAIN}.entity.sensor.last_event.state.opening_by": "Opening by {name}",
        f"component.{DOMAIN}.entity.sensor.last_event.state.nfc_tag_type_3": "User Badge",
        f"component.{DOMAIN}.entity.sensor.last_event.state.diagnostic_error_integrity": "Integrity Error",
        f"component.{DOMAIN}.entity.sensor.last_event.state.power_off_reason_2": "Watchdog Reboot",
        f"component.{DOMAIN}.entity.sensor.last_event.state.door_opened": "Door Opened",
    }

async def test_async_enrich_log_entry_full_flow(hass, log_processor, mock_translations):
    """Test the full enrichment flow of async_enrich_log_entry."""
    tag_id = "5A3EDAE0"
    tag_name = "My Test Badge"
    
    # Mock Tag Registry
    mock_tags_helper = MagicMock()
    mock_tags_helper.data = {tag_id: {"name": tag_name, "last_scanned": None}}
    mock_tags_helper.async_update_item = AsyncMock()
    hass.data["tag"] = {"tags": mock_tags_helper}

    log = BoksLogEntry(
        opcode=BoksHistoryEvent.NFC_OPENING,
        payload=bytearray.fromhex("03045a3edae0"),
        timestamp=1700000000,
        event_type="nfc_opening",
        description="nfc_opening",
        extra_data={"tag_type": 3, "tag_uid": tag_id}
    )

    enriched = await log_processor.async_enrich_log_entry(log, mock_translations)

    assert enriched["event_type"] == "nfc_opening"
    assert enriched["extra_data"]["tag_name"] == tag_name
    assert enriched["description"] == f"Opening by {tag_name}"
    assert mock_tags_helper.async_update_item.called

def test_translate_base_description(log_processor, mock_translations):
    """Test _translate_base_description static method."""
    desc = log_processor._translate_base_description("door_opened", mock_translations)
    assert desc == "Door Opened"
    
    # Fallback
    desc = log_processor._translate_base_description("unknown_event", mock_translations)
    assert desc == "unknown_event"

def test_enrich_diagnostic_error(log_processor, mock_translations):
    """Test _enrich_diagnostic_error static method."""
    extra_data = {"error_description": "diagnostic_error_integrity"}
    
    # Matching error
    desc = log_processor._enrich_diagnostic_error("error", extra_data, mock_translations, "Base Error")
    assert desc == "Base Error: Integrity Error"
    assert extra_data["error_description"] == "Integrity Error"
    
    # Not an error event
    desc = log_processor._enrich_diagnostic_error("info", extra_data, mock_translations, "Base Info")
    assert desc == "Base Info"

def test_enrich_power_off_reason(log_processor, mock_translations):
    """Test _enrich_power_off_reason static method."""
    extra_data = {"reason_code": 2}
    
    # Matching reason
    desc = log_processor._enrich_power_off_reason("power_off", extra_data, mock_translations, "Off")
    assert desc == "Off: Watchdog Reboot"
    assert extra_data["reason_text"] == "Watchdog Reboot"
    
    # Unknown reason code
    extra_data = {"reason_code": 99}
    desc = log_processor._enrich_power_off_reason("power_off", extra_data, mock_translations, "Off")
    assert desc == "Off"

def test_enrich_tag_type(log_processor, mock_translations):
    """Test _enrich_tag_type static method."""
    extra_data = {"tag_type": 3}
    log_processor._enrich_tag_type(extra_data, mock_translations)
    assert extra_data["tag_type_description"] == "User Badge"
    
    # Unknown type
    extra_data = {"tag_type": 99}
    log_processor._enrich_tag_type(extra_data, mock_translations)
    assert extra_data["tag_type_description"] == "Type 99"

async def test_resolve_tag_name(hass, log_processor):
    """Test _resolve_tag_name instance method."""
    tag_id = "AABBCCDD"
    tag_name = "Registry Name"
    
    # Case 1: Registry lookup
    mock_tags_helper = MagicMock()
    mock_tags_helper.data = {tag_id: {"name": tag_name}}
    hass.data["tag"] = {"tags": mock_tags_helper}
    
    resolved = await log_processor._resolve_tag_name({"tag_uid": tag_id})
    assert resolved == tag_name
    
    # Case 2: Already has name
    resolved = await log_processor._resolve_tag_name({"tag_uid": tag_id, "tag_name": "Existing"})
    assert resolved == "Existing"
    
    # Case 3: Tag not in registry
    resolved = await log_processor._resolve_tag_name({"tag_uid": "UNKNOWN"})
    assert resolved is None

def test_format_nfc_description(log_processor, mock_translations):
    """Test _format_nfc_description static method."""
    # Case 1: Named tag
    extra_data = {"tag_uid": "UID", "tag_name": "My Name"}
    desc = log_processor._format_nfc_description("nfc_opening", extra_data, mock_translations, "Base")
    assert desc == "Opening by My Name"
    
    # Case 2: Unnamed tag with type description
    extra_data = {"tag_uid": "UID", "tag_type_description": "User Badge"}
    desc = log_processor._format_nfc_description("nfc_opening", extra_data, mock_translations, "Base")
    assert desc == "Opening by User Badge (UID)"
    
    # Case 3: Not an NFC opening
    desc = log_processor._format_nfc_description("door_opened", {}, mock_translations, "Base")
    assert desc == "Base"

def test_should_update_last_scanned(log_processor):
    """Test _should_update_last_scanned static method."""
    now = dt_util.utcnow()
    past = datetime(2020, 1, 1, tzinfo=dt_util.UTC)
    future = datetime(2099, 1, 1, tzinfo=dt_util.UTC)
    
    # No previous date -> Update
    assert log_processor._should_update_last_scanned(None, now) is True
    
    # Older date -> Update
    assert log_processor._should_update_last_scanned(past, now) is True
    assert log_processor._should_update_last_scanned(past.isoformat(), now) is True
    
    # Newer date -> No update
    assert log_processor._should_update_last_scanned(future, now) is False
    assert log_processor._should_update_last_scanned(future.isoformat(), now) is False

async def test_update_tag_last_scanned(hass, log_processor):
    """Test _update_tag_last_scanned instance method."""
    tag_id = "UID123"
    mock_tags_helper = MagicMock()
    mock_tags_helper.data = {tag_id: {"last_scanned": None}}
    mock_tags_helper.async_update_item = AsyncMock()
    hass.data["tag"] = {"tags": mock_tags_helper}
    
    # Valid update
    await log_processor._update_tag_last_scanned("nfc_opening", 1700000000, {"tag_uid": tag_id})
    assert mock_tags_helper.async_update_item.called
    
    # Not an NFC opening -> No update
    mock_tags_helper.async_update_item.reset_mock()
    await log_processor._update_tag_last_scanned("door_opened", 1700000000, {"tag_uid": tag_id})
    assert not mock_tags_helper.async_update_item.called