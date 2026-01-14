"""The Boks integration."""
import importlib
import logging
import voluptuous as vol
import json
import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import DOMAIN
from .coordinator import BoksDataUpdateCoordinator
from .services import async_setup_services

# Define the CONFIG_SCHEMA as an empty schema for config entries only
CONFIG_SCHEMA = vol.Schema({}, extra=vol.ALLOW_EXTRA)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.LOCK, Platform.BUTTON, Platform.EVENT, Platform.TODO, Platform.UPDATE]

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Boks component."""
    
    # Register all services
    await async_setup_services(hass)
    
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Boks from a config entry."""

    # Ensure options are populated with defaults if missing
    from .const import DEFAULT_SCAN_INTERVAL, DEFAULT_FULL_REFRESH_INTERVAL
    
    options_update = {}
    if "scan_interval" not in entry.options:
        options_update["scan_interval"] = DEFAULT_SCAN_INTERVAL
    if "full_refresh_interval" not in entry.options:
        options_update["full_refresh_interval"] = DEFAULT_FULL_REFRESH_INTERVAL
    
    if options_update:
        new_options = {**entry.options, **options_update}
        hass.config_entries.async_update_entry(entry, options=new_options)
        _LOGGER.debug(f"Updated config entry options with defaults: {options_update}")

    coordinator = BoksDataUpdateCoordinator(hass, entry)

    try:
        await coordinator.async_config_entry_first_refresh()
    except UpdateFailed as ex:
        raise ConfigEntryNotReady(f"Coordinator init failed: {ex}") from ex

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Cache translations for Logbook usage (Manual Load)
    try:
        lang = hass.config.language
        integration_path = os.path.dirname(__file__)
        translation_path = os.path.join(integration_path, "translations", f"{lang}.json")

        if not os.path.exists(translation_path):
            _LOGGER.warning("Translation file for '%s' not found at %s, falling back to 'en'", lang, translation_path)
            translation_path = os.path.join(integration_path, "translations", "en.json")

        if os.path.exists(translation_path):
            def load_json(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)

            translations_json = await hass.async_add_executor_job(load_json, translation_path)

            try:
                state_translations = translations_json.get("entity", {}).get("event", {}).get("logs", {}).get("state", {})
                hass.data[DOMAIN]["translations"] = state_translations
            except AttributeError:
                hass.data[DOMAIN]["translations"] = {}
                _LOGGER.warning("Could not extract state translations from JSON structure")
        else:
             hass.data[DOMAIN]["translations"] = {}
             _LOGGER.warning("No translation file found at %s (fallback failed)", translation_path)

    except Exception as e:
        _LOGGER.warning("Failed to manually load translations for Logbook: %s", e)
        hass.data[DOMAIN]["translations"] = {}

    for platform in PLATFORMS:
        await hass.async_add_executor_job(
            importlib.import_module, f".{platform}", __package__
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""

    # Check if master code has changed
    new_master_code = entry.options.get("master_code")

    if new_master_code:
        new_master_code = new_master_code.strip().upper()
        _LOGGER.info(f"Master code change requested for {entry.title}. New code: {new_master_code}")

        new_data = dict(entry.data)
        new_data["master_code"] = new_master_code
        hass.config_entries.async_update_entry(entry, data=new_data)
        _LOGGER.info(f"Master code updated successfully in configuration to {new_master_code}.")

        new_options = dict(entry.options)
        if "master_code" in new_options:
            del new_options["master_code"]

        hass.config_entries.async_update_entry(
            entry,
            options=new_options
        )

    await hass.config_entries.async_reload(entry.entry_id)