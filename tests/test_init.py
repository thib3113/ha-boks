"""Tests for the Boks integration."""
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.boks.const import DOMAIN


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
    # IMPORTANT: On utilise new_callable=AsyncMock pour que le mock soit "awaitable"
    with patch("custom_components.boks.async_setup_entry", new_callable=AsyncMock) as mock_setup:
        mock_setup.return_value = True

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
    with patch("custom_components.boks.async_setup_entry", new_callable=AsyncMock) as mock_setup:
        mock_setup.return_value = True

        result = await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert result is True

    # Unload the integration
    # Pareil ici, async_unload_entry est async, il faut un AsyncMock
    with patch("custom_components.boks.async_unload_entry", new_callable=AsyncMock) as mock_unload:
        mock_unload.return_value = True

        await hass.config_entries.async_unload(entry.entry_id)
