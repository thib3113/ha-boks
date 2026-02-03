"""Parcels Logic Controller for Boks."""
import logging
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from ..const import DOMAIN
from .utils import format_parcel_item, generate_random_code, parse_parcel_string

if TYPE_CHECKING:
    from ..coordinator import BoksDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

class BoksParcelsController:
    """Controller for Parcel operations."""

    def __init__(self, hass: HomeAssistant, coordinator: "BoksDataUpdateCoordinator"):
        self.hass = hass
        self.coordinator = coordinator

    async def add_parcel(self, description: str, entity_id: str | None = None, device_id: str | None = None) -> dict:
        """Add a parcel to the todo list."""
        _LOGGER.info("Add Parcel requested: %s", description)
        target_entity_id = entity_id

        # 1. Resolve Target Entity ID if not provided
        if not target_entity_id:
            # If device_id provided, find entity for that device
            if device_id:
                entity_registry = er.async_get(self.hass)
                entries = entity_registry.entities.values()
                for entry in entries:
                    if entry.device_id == device_id and entry.domain == "todo":
                        target_entity_id = entry.entity_id
                        break

                if not target_entity_id:
                     raise HomeAssistantError(
                         translation_domain=DOMAIN,
                         translation_key="todo_entity_not_found_for_device",
                         translation_placeholders={"target_device_id": device_id}
                     )

            # If no device_id, find entity for current coordinator's entry
            else:
                config_entry_id = self.coordinator.entry.entry_id
                entity_registry = er.async_get(self.hass)
                entries = entity_registry.entities.values()
                for entry in entries:
                    if entry.config_entry_id == config_entry_id and entry.domain == "todo":
                        target_entity_id = entry.entity_id
                        break

                if not target_entity_id:
                     raise HomeAssistantError(
                         translation_domain=DOMAIN,
                         translation_key="todo_entity_not_found",
                         translation_placeholders={"target_entity_id": "auto-discovery"}
                     )

        # 2. Get Actual Entity Object
        component = self.hass.data.get("entity_components", {}).get("todo")
        if not component:
             raise HomeAssistantError(
                 translation_domain=DOMAIN,
                 translation_key="todo_integration_not_loaded"
             )

        todo_entity = component.get_entity(target_entity_id)

        if not todo_entity:
             raise HomeAssistantError(
                 translation_domain=DOMAIN,
                 translation_key="todo_entity_not_found",
                 translation_placeholders={"target_entity_id": target_entity_id}
             )

        # 3. Verify it's a Boks entity (Check capability)
        if not hasattr(todo_entity, "async_create_parcel"):
             raise HomeAssistantError(
                 translation_domain=DOMAIN,
                 translation_key="entity_not_parcel_list",
                 translation_placeholders={"target_entity_id": target_entity_id}
             )

        # 4. Generate/Parse Code and Create Parcel
        has_config_key = getattr(todo_entity, "_has_config_key", False)
        code_in_desc, _ = parse_parcel_string(description)
        generated_code = None
        force_sync = False

        if not code_in_desc:
            generated_code = generate_random_code()
            if has_config_key:
                force_sync = True
            formatted_description = format_parcel_item(generated_code, description or "Parcel")
        else:
            formatted_description = description
            generated_code = code_in_desc
            force_sync = False

        await todo_entity.async_create_parcel(formatted_description, force_background_sync=force_sync)
        _LOGGER.info("Add Parcel completed. Code: %s", generated_code)

        return {"code": generated_code}
