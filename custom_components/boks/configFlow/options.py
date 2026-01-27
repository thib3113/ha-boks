from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from ..const import (
    BOKS_CHAR_MAP,
    CONF_ANONYMIZE_LOGS,
    CONF_MASTER_CODE,
    DEFAULT_FULL_REFRESH_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
)


class BoksOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Boks options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.entry = config_entry

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
                        default=self.entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL),
                    ): int,
                    vol.Optional(
                        "full_refresh_interval",
                        default=self.entry.options.get("full_refresh_interval", DEFAULT_FULL_REFRESH_INTERVAL),
                    ): int,
                    vol.Optional(
                        CONF_MASTER_CODE,
                        description={"suggested_value": self.entry.options.get(CONF_MASTER_CODE)},
                    ): str,
                    vol.Optional(
                        CONF_ANONYMIZE_LOGS,
                        default=self.entry.options.get(CONF_ANONYMIZE_LOGS, False),
                    ): bool,
                }
            ),
            errors=errors,
        )
