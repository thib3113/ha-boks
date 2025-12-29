"""Config flow for Boks integration."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.core import callback
from homeassistant.components import bluetooth

from .const import (
    DOMAIN, 
    CONF_CONFIG_KEY, 
    CONF_MASTER_CODE, 
    BOKS_CHAR_MAP, 
    CONF_MASTER_KEY, 
    DEFAULT_SCAN_INTERVAL, 
    DEFAULT_FULL_REFRESH_INTERVAL,
    CONF_ANONYMIZE_LOGS
)

_LOGGER = logging.getLogger(__name__)

class BoksConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Boks."""
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return BoksOptionsFlowHandler(config_entry)

    def __init__(self):
        """Initialize."""
        self._discovery_info = None

    async def async_step_bluetooth(self, discovery_info: "BluetoothServiceInfoBleak") -> FlowResult:
        """Handle the bluetooth discovery step."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        self._discovery_info = discovery_info
        self.context["title_placeholders"] = {"name": discovery_info.name}

        return await self.async_step_user()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the manual entry step."""
        errors = {}

        # Defaults
        default_address = None
        default_master_code = ""
        default_credential = ""

        if self._discovery_info:
            default_address = self._discovery_info.address

        if user_input is not None:
            # Preserve input values for the form retry
            default_address = user_input.get(CONF_ADDRESS, default_address)
            default_master_code = user_input.get(CONF_MASTER_CODE, default_master_code)
            default_credential = user_input.get("credential", default_credential)

            # 0. Normalize Address
            raw_addr = user_input[CONF_ADDRESS]
            # Remove all non-alphanumeric characters
            clean_addr = "".join(c for c in raw_addr if c.isalnum()).upper()
            
            if len(clean_addr) == 12:
                # Reformat to XX:XX:XX:XX:XX:XX
                address = ":".join(clean_addr[i:i+2] for i in range(0, 12, 2))
            else:
                # Keep original to allow standard validation failure or if it's already weird
                address = raw_addr.strip().upper()

            master_code_input = user_input[CONF_MASTER_CODE].strip().upper()
            credential = user_input.get("credential", "").strip().upper()

            config_key = None
            master_key = None

            # 1. Check if device is connectable (if manually entered)
            # We try with connectable=True first (Best Practice)
            device = bluetooth.async_ble_device_from_address(self.hass, address, connectable=True)
            if not device:
                 # Fallback: Check if it exists but is not connectable (Workaround for some setups)
                 device = bluetooth.async_ble_device_from_address(self.hass, address, connectable=False)
                 if device:
                     _LOGGER.warning("Device %s found via non-connectable discovery. Connection might fail if no active adapter is available.", address)
                 else:
                     # Device not found at all
                     errors["base"] = "unknown_device"

            # 2. Validate Master Code (Must be 6 chars, 0-9, A, B)
            if not (len(master_code_input) == 6 and all(c in BOKS_CHAR_MAP for c in master_code_input)):
                errors[CONF_MASTER_CODE] = "invalid_master_code_format"

            # 3. Validate Credential (Master Key or Config Key) - Optional
            if credential:
                length = len(credential)
                try:
                    # Verify hex content
                    int(credential, 16)

                    if length == 64: # Master Key
                        master_key = credential
                        config_key = master_key[-8:]
                    elif length == 8: # Config Key
                        config_key = credential
                    else:
                        errors["credential"] = "invalid_credential_format"
                except ValueError:
                    errors["credential"] = "invalid_credential_format"

            if not errors:
                await self.async_set_unique_id(address)
                self._abort_if_unique_id_configured()

                data = {
                    CONF_ADDRESS: address,
                    CONF_MASTER_CODE: master_code_input,
                }

                # Store the key (Master or Config) if provided
                if config_key:
                    data[CONF_CONFIG_KEY] = config_key
                if master_key:
                    data[CONF_MASTER_KEY] = master_key

                # Generate a default name
                name = "Boks"
                if self._discovery_info and self._discovery_info.name:
                    name = self._discovery_info.name
                elif device and device.name:
                    name = device.name

                # If name is generic, append short Address to ensure uniqueness and better identification
                if name in ["Boks", "Boks Parcel Box", "Boks ONE"]:
                    short_address = address.replace(":", "")[-6:]
                    name = f"{name} {short_address}"

                data[CONF_NAME] = name

                return self.async_create_entry(
                    title=data[CONF_NAME],
                    data=data,
                    options={
                        "scan_interval": DEFAULT_SCAN_INTERVAL,
                        "full_refresh_interval": DEFAULT_FULL_REFRESH_INTERVAL,
                    }
                )

        # Form Schema
        schema = {
            vol.Required(CONF_ADDRESS, default=default_address or vol.UNDEFINED): str,
            vol.Required(CONF_MASTER_CODE, default=default_master_code): str,
            vol.Optional("credential", default=default_credential): str,
        }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema),
            errors=errors,
        )

class BoksOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Boks options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        errors = {}

        if user_input is not None:
            # Validate and normalize Master Code if provided
            if user_input.get(CONF_MASTER_CODE):
                code = user_input[CONF_MASTER_CODE].strip().upper()
                if not (len(code) == 6 and all(c in BOKS_CHAR_MAP for c in code)):
                    errors[CONF_MASTER_CODE] = "invalid_master_code_format"
                else:
                    user_input[CONF_MASTER_CODE] = code

            if not errors:
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "scan_interval",
                        default=self.config_entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL),
                    ): int,
                    vol.Optional(
                        "full_refresh_interval",
                        default=self.config_entry.options.get("full_refresh_interval", DEFAULT_FULL_REFRESH_INTERVAL),
                    ): int,
                    vol.Optional(
                        CONF_MASTER_CODE,
                        description={"suggested_value": self.config_entry.options.get(CONF_MASTER_CODE)},
                    ): str,
                    vol.Optional(
                        CONF_ANONYMIZE_LOGS,
                        default=self.config_entry.options.get(CONF_ANONYMIZE_LOGS, False),
                    ): bool,
                }
            ),
            errors=errors,
        )
