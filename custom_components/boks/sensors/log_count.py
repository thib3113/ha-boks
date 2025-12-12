"""Log count sensor for Boks."""
import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import CONF_ADDRESS
from homeassistant.config_entries import ConfigEntry

from ..entity import BoksEntity
from ..coordinator import BoksDataUpdateCoordinator
from ..ble.const import BoksNotificationOpcode
from ..ble.protocol import BoksProtocol
from homeassistant.const import EntityCategory

_LOGGER = logging.getLogger(__name__)


class BoksLogCountSensor(BoksEntity, SensorEntity):
    """Representation of a Boks Log Count Sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "log_count"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: BoksDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.data[CONF_ADDRESS]}_log_count"
        self._callback_registered = False

    @property
    def suggested_object_id(self) -> str | None:
        """Return the suggested object id."""
        return "log_count"

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self.coordinator.data.get("log_count", 0)

    async def async_added_to_hass(self) -> None:
        """Register opcode callback when entity is added to hass."""
        await super().async_added_to_hass()
        
        if not self._callback_registered:
            self.coordinator.register_opcode_callback(
                BoksNotificationOpcode.NOTIFY_LOGS_COUNT,
                self._handle_logs_count_notification
            )
            self._callback_registered = True
            _LOGGER.debug("Registered opcode callback for log count sensor %s", self._attr_unique_id)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister opcode callback when entity is removed from hass."""
        if self._callback_registered:
            self.coordinator.unregister_opcode_callback(
                BoksNotificationOpcode.NOTIFY_LOGS_COUNT,
                self._handle_logs_count_notification
            )
            self._callback_registered = False
            _LOGGER.debug("Unregistered opcode callback for log count sensor %s", self._attr_unique_id)
        
        await super().async_will_remove_from_hass()

    def _handle_logs_count_notification(self, data: bytearray) -> None:
        """Handle logs count notification."""
        try:
            log_count = BoksProtocol.parse_logs_count(data)
            
            if log_count is not None:
                # Update coordinator data
                if self.coordinator.data is None:
                    self.coordinator.data = {}
                
                self.coordinator.data["log_count"] = log_count
                _LOGGER.debug("Updated log count to %d", log_count)
                
                # Notify listeners of the update
                self.coordinator.async_set_updated_data(self.coordinator.data)
        except Exception as e:
            _LOGGER.error("Error handling logs count notification: %s", e)