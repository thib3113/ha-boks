"""Tests for the PacketFactory logic."""
from unittest.mock import patch
import pytest
from custom_components.boks.packets.factory import PacketFactory
from custom_components.boks.packets.base import BoksRXPacket
from custom_components.boks.ble.const import BoksHistoryEvent
from custom_components.boks.packets.rx.code_ble_valid import CodeBleValidPacket
from custom_components.boks.packets.rx.code_ble_invalid import CodeBleInvalidPacket
from custom_components.boks.packets.rx.power_off import PowerOffPacket
from custom_components.boks.packets.rx.error_log import ErrorLogPacket
from custom_components.boks.packets.rx.door_opened import DoorOpenedPacket
from custom_components.boks.packets.rx.key_opening import KeyOpeningPacket
from custom_components.boks.packets.rx.nfc_opening import NfcOpeningPacket
from custom_components.boks.packets.rx.nfc_tag_registering_scan import NfcTagRegisteringScanPacket

def build_rx_packet(opcode: int, payload: bytes) -> bytearray:
    """Helper to build a valid framed RX packet."""
    packet = bytearray()
    packet.append(opcode)
    packet.append(len(payload))
    packet.extend(payload)
    checksum = sum(packet) & 0xFF
    packet.append(checksum)
    return packet

# Mock time to ensure consistent timestamps in tests
@pytest.fixture
def mock_time():
    with patch("time.time") as mock_time:
        mock_time.return_value = 1700000000.0 # Fixed timestamp
        yield mock_time

def test_factory_code_ble_valid(mock_time):
    """Test factory creates CodeBleValidPacket (0x86)."""
    # 0x86 = CODE_BLE_VALID
    # Payload: Age(3 bytes) + Code(6 bytes)
    payload = bytes.fromhex("000064313233343536")
    data = build_rx_packet(0x86, payload)
    
    packet = PacketFactory.from_rx_data(data)
    
    assert isinstance(packet, CodeBleValidPacket)
    assert packet.opcode == BoksHistoryEvent.CODE_BLE_VALID

def test_factory_code_ble_invalid(mock_time):
    """Test factory creates CodeBleInvalidPacket (0x88)."""
    # 0x88 = CODE_BLE_INVALID
    payload = bytes.fromhex("0000643132FF003536")
    data = build_rx_packet(0x88, payload)
    
    packet = PacketFactory.from_rx_data(data)
    
    assert isinstance(packet, CodeBleInvalidPacket)

def test_factory_power_off(mock_time):
    """Test factory creates PowerOffPacket (0x94)."""
    # 0x94 = POWER_OFF
    payload = bytes.fromhex("00000A02")
    data = build_rx_packet(0x94, payload)
    
    packet = PacketFactory.from_rx_data(data)
    
    assert isinstance(packet, PowerOffPacket)

def test_factory_error_log(mock_time):
    """Test factory creates ErrorLogPacket (0xA0)."""
    # 0xA0 = ERROR
    payload = bytes.fromhex("00000A08BC001122")
    data = build_rx_packet(0xA0, payload)
    
    packet = PacketFactory.from_rx_data(data)
    
    assert isinstance(packet, ErrorLogPacket)

def test_factory_door_opened(mock_time):
    """Test factory creates DoorOpenedPacket (0x91)."""
    # 0x91 = DOOR_OPENED
    payload = bytes.fromhex("0000FF")
    data = build_rx_packet(0x91, payload)
    
    packet = PacketFactory.from_rx_data(data)
    
    assert isinstance(packet, DoorOpenedPacket)

def test_factory_key_opening(mock_time):
    """Test factory creates KeyOpeningPacket (0x99)."""
    # 0x99 = KEY_OPENING
    payload = bytes.fromhex("00000A112233")
    data = build_rx_packet(0x99, payload)
    
    packet = PacketFactory.from_rx_data(data)
    
    assert isinstance(packet, KeyOpeningPacket)

def test_factory_invalid_opcode():
    """Test factory returns generic packet for unknown opcode."""
    payload = bytes.fromhex("000000")
    data = build_rx_packet(0xFF, payload)
    
    packet = PacketFactory.from_rx_data(data)
    
    assert type(packet) == BoksRXPacket
    assert packet.opcode == 0xFF

def test_factory_nfc_opening(mock_time):
    """Test factory creates NfcOpeningPacket (0xA1)."""
    # 0xA1 = NFC_OPENING
    payload = bytes.fromhex("00000A0104A1B2C3D4")
    data = build_rx_packet(0xA1, payload)
    
    packet = PacketFactory.from_rx_data(data)
    
    assert isinstance(packet, NfcOpeningPacket)

def test_factory_nfc_tag_registering_scan(mock_time):
    """Test factory creates NfcTagRegisteringScanPacket (0xA2)."""
    # 0xA2 = NFC_TAG_REGISTERING_SCAN
    payload = bytes.fromhex("00000A0304AABBCCDD")
    data = build_rx_packet(0xA2, payload)
    
    packet = PacketFactory.from_rx_data(data)
    
    assert isinstance(packet, NfcTagRegisteringScanPacket)
