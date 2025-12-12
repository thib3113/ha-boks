"""Boks BLE package."""

from .device import BoksBluetoothDevice
from ..errors import BoksError, BoksAuthError, BoksCommandError
from .log_entry import BoksLogEntry
from .const import (
    BoksServiceUUID,
    BoksCommandOpcode,
    BoksNotificationOpcode,
    BoksHistoryEvent,
    BoksPowerOffReason,
)

__all__ = [
    "BoksBluetoothDevice",
    "BoksError",
    "BoksAuthError",
    "BoksCommandError",
    "BoksLogEntry",
    "BoksServiceUUID",
    "BoksCommandOpcode",
    "BoksNotificationOpcode",
    "BoksHistoryEvent",
    "BoksPowerOffReason",
]