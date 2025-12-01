"""Tests for the Boks integration."""
from unittest.mock import patch

from homeassistant import config_entries
from custom_components.boks.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_setup_entry(hass: HomeAssistant) -> None:
    """Test successful setup of the integration."""
    # Create a mock config entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Boks",
        data={
            "mac": "AA:BB:CC:DD:EE:FF",
            "master_code": "12345A",
            "name": "Boks AAABBB",
        },
    )
    entry.add_to_hass(hass)

    # Setup the integration
    with patch("custom_components.boks.async_setup_entry", return_value=True):
        result = await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert result is True


async def test_unload_entry(hass: HomeAssistant) -> None:
    """Test successful unload of the integration."""
    # Create a mock config entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Boks",
        data={
            "mac": "AA:BB:CC:DD:EE:FF",
            "master_code": "12345A",
            "name": "Boks AAABBB",
        },
    )
    entry.add_to_hass(hass)

    # Setup the integration
    with patch("custom_components.boks.async_setup_entry", return_value=True):
        result = await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert result is True

    # Unload the integration
    with patch("custom_components.boks.async_unload_entry", return_value=True):
        await hass.config_entries.async_unload(entry.entry_id)