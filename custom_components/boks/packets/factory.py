"""Factory to create packet objects from raw data."""

from .base import BoksRXPacket
from .rx.ble_reboot import BleRebootPacket
from .rx.block_reset import BlockResetPacket
from .rx.code_ble_invalid import CodeBleInvalidPacket
from .rx.code_ble_valid import CodeBleValidPacket
from .rx.code_counts import CodeCountsPacket
from .rx.code_key_invalid import CodeKeyInvalidPacket
from .rx.code_key_valid import CodeKeyValidPacket
from .rx.door_closed import DoorClosedPacket
from .rx.door_opened import DoorOpenedPacket
from .rx.door_status import DoorStatusPacket
from .rx.end_history import EndHistoryPacket
from .rx.error_log import ErrorLogPacket
from .rx.error_response import ErrorResponsePacket
from .rx.history_erase import HistoryErasePacket
from .rx.key_opening import KeyOpeningPacket
from .rx.log_count import LogCountPacket
from .rx.nfc_error import NfcErrorPacket
from .rx.nfc_opening import NfcOpeningPacket
from .rx.nfc_scan_result import NfcScanResultPacket
from .rx.nfc_tag_registered import NfcTagRegisteredPacket
from .rx.nfc_tag_registering_scan import NfcTagRegisteringScanPacket
from .rx.open_code_result import OpenCodeResultPacket
from .rx.operation_result import OperationResultPacket
from .rx.power_off import PowerOffPacket
from .rx.power_on import PowerOnPacket


class PacketFactory:
    """Factory for creating Boks packet objects."""

    _RX_MAP: dict[int, type[BoksRXPacket]] = {}

    @classmethod
    def _build_map(cls):
        """Build the opcode to class mapping once."""
        if cls._RX_MAP:
            return

        classes = [
            CodeBleValidPacket, CodeKeyValidPacket, CodeBleInvalidPacket, CodeKeyInvalidPacket,
            DoorOpenedPacket, DoorClosedPacket, HistoryErasePacket, BlockResetPacket,
            PowerOnPacket, BleRebootPacket, KeyOpeningPacket, PowerOffPacket,
            NfcOpeningPacket, NfcTagRegisteringScanPacket, EndHistoryPacket, CodeCountsPacket,
            DoorStatusPacket, LogCountPacket, NfcTagRegisteredPacket,
            OperationResultPacket, ErrorResponsePacket, ErrorLogPacket,
            NfcScanResultPacket, NfcErrorPacket, OpenCodeResultPacket
        ]

        for cls_item in classes:
            opcodes = cls_item.OPCODES
            if isinstance(opcodes, list):
                for op in opcodes:
                    cls._RX_MAP[op] = cls_item
            elif opcodes is not None:
                cls._RX_MAP[opcodes] = cls_item

    @classmethod
    def from_rx_data(cls, data: bytearray) -> BoksRXPacket:
        """Create an RX packet object from raw bytes using the registered map."""
        if not data or len(data) < 1:
            return BoksRXPacket(0, data)

        cls._build_map()
        opcode = data[0]

        packet_class = cls._RX_MAP.get(opcode)
        if packet_class:
            try:
                # Try passing opcode if required by signature (based on BoksRXPacket signature)
                return packet_class(opcode, data)
            except TypeError:
                # Fallback for classes that only take data (constant opcode ones)
                return packet_class(data)

        # Fallback to generic RX packet
        return BoksRXPacket(opcode, data)
