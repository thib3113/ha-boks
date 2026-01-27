"""Code count sensors for Boks."""
import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS

from ..ble.const import BoksNotificationOpcode
from ..coordinator import BoksDataUpdateCoordinator
from ..entity import BoksEntity
from ..packets.factory import PacketFactory
from ..packets.rx.code_counts import CodeCountsPacket

_LOGGER = logging.getLogger(__name__)


class BoksCodeCountSensor(BoksEntity, SensorEntity):
    """Representation of a Boks Code Count Sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: BoksDataUpdateCoordinator, entry: ConfigEntry, code_type: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._code_type = code_type
        self._attr_translation_key = f"{code_type}_codes_count"
        self._attr_unique_id = f"{entry.data[CONF_ADDRESS]}_{code_type}_codes_count"
        self._callback_registered = False

    @property
    def suggested_object_id(self) -> str | None:
        """Return the suggested object id."""
        return f"{self._code_type}_codes"

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._code_type, 0)

    async def async_added_to_hass(self) -> None:
        """Register opcode callback when entity is added to hass."""
        await super().async_added_to_hass()

        if not self._callback_registered:
            self.coordinator.register_opcode_callback(
                BoksNotificationOpcode.NOTIFY_CODES_COUNT,
                self._handle_codes_count_notification
            )
            self._callback_registered = True
            _LOGGER.debug("Registered opcode callback for code count sensor %s", self._attr_unique_id)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister opcode callback when entity is removed from hass."""
        if self._callback_registered:
            self.coordinator.unregister_opcode_callback(
                BoksNotificationOpcode.NOTIFY_CODES_COUNT,
                self._handle_codes_count_notification
            )
            self._callback_registered = False
            _LOGGER.debug("Unregistered opcode callback for code count sensor %s", self._attr_unique_id)

        await super().async_will_remove_from_hass()

    def _handle_codes_count_notification(self, data: bytearray) -> None:
        """Handle codes count notification."""
        try:
            packet = PacketFactory.from_rx_data(data)

            if isinstance(packet, CodeCountsPacket):
                # Update coordinator data
                if self.coordinator.data is None:
                    self.coordinator.data = {}

                # Update only the relevant code type count
                if self._code_type == "master":
                    count = packet.master_count
                else:
                    count = packet.single_use_count

                self.coordinator.data[self._code_type] = count
                _LOGGER.debug("Updated %s code count to %d", self._code_type, count)

                # Notify listeners of the update
                self.coordinator.async_set_updated_data(self.coordinator.data)
        except Exception as e:
            _LOGGER.error("Error handling codes count notification: %s", e)
