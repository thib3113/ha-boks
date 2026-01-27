"""Tests for the Boks log processor."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from custom_components.boks.logic.log_processor import BoksLogProcessor
from custom_components.boks.ble.const import BoksHistoryEvent
from custom_components.boks.packets.base import BoksRXPacket

@pytest.fixture
def log_processor(hass):
    """Fixture for BoksLogProcessor."""
    return BoksLogProcessor(hass, "AA:BB:CC:DD:EE:FF")

@pytest.fixture
def mock_translations():
    """Mock translations dictionary."""
    return {
        "component.boks.entity.sensor.last_event.state.nfc_opening": "NFC Opening",
        "component.boks.entity.sensor.last_event.state.opening_by": "Opening by {name}",
        "component.boks.entity.sensor.last_event.state.nfc_tag_type_3": "User Badge",
    }

class MockPacket(BoksRXPacket):
    def __init__(self, opcode, event_type, extra_data):
        self.opcode = opcode
        self._event_type = event_type
        self._extra_data = extra_data
        self.payload = b""
        self.timestamp = 1700000000

    @property
    def event_type(self):
        return self._event_type

    @property
    def extra_data(self):
        return self._extra_data

async def test_async_enrich_log_entry_full_flow(hass, log_processor, mock_translations):
    """Test the full enrichment flow of async_enrich_log_entry."""
    tag_id = "5A3EDAE0"
    tag_name = "My Test Badge"

    # Mock Tag Registry
    mock_tags_helper = MagicMock()
    mock_tags_helper.data = {tag_id: {"name": tag_name, "last_scanned": None}}
    mock_tags_helper.async_update_item = AsyncMock()
    hass.data["tag"] = {"tags": mock_tags_helper}

    log = MockPacket(
        opcode=BoksHistoryEvent.NFC_OPENING,
        event_type="nfc_opening",
        extra_data={"tag_type": 3, "tag_uid": tag_id}
    )

    enriched = await log_processor.async_enrich_log_entry(log, mock_translations)

    assert enriched["event_type"] == "nfc_opening"
    assert enriched["extra_data"]["tag_name"] == tag_name
    assert enriched["description"] == f"Opening by {tag_name}"
    assert mock_tags_helper.async_update_item.called
