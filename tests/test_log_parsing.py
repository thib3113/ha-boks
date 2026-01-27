"""Tests for the Boks log entry parsing logic."""
from unittest.mock import patch

import pytest
from custom_components.boks.packets.factory import PacketFactory
from custom_components.boks.ble.const import BoksHistoryEvent

def _create_packet(opcode: int, payload: bytes) -> bytearray:
    """Helper to create a framed packet."""
    packet = bytearray()
    packet.append(opcode)
    packet.append(len(payload))
    packet.extend(payload)
    # Checksum (dummy 0xFF, factory doesn't check it unless verify_checksum called on instance)
    packet.append(0xFF)
    return packet

def test_parse_code_ble_valid():
    """Test parsing a valid BLE code event (0x86)."""
    # Age(3) + Code(6)
    payload = bytes.fromhex("000064313233343536")
    data = _create_packet(0x86, payload)
    
    packet = PacketFactory.from_rx_data(data)

    assert packet is not None
    assert packet.opcode == BoksHistoryEvent.CODE_BLE_VALID
    assert packet.event_type == "code_ble_valid"
    assert packet.age == 100
    assert packet.extra_data["code"] == "123456"

def test_parse_door_opened():
    """Test parsing a simple DOOR_OPENED event (0x91)."""
    payload = bytes.fromhex("0000FF") # Age 255
    data = _create_packet(0x91, payload)

    packet = PacketFactory.from_rx_data(data)

    assert packet is not None
    assert packet.opcode == BoksHistoryEvent.DOOR_OPENED
    assert packet.event_type == "door_opened"
    assert packet.age == 255

def test_parse_nfc_opening_classic():
    """Test parsing standard Mifare Classic NFC opening (0xA1)."""
    # Age(3) + TagType(1) + UIDLen(1) + UID(4)
    # 01 04 A1B2C3D4
    payload = bytes.fromhex("00000A0104A1B2C3D4")
    data = _create_packet(0xA1, payload)
    
    packet = PacketFactory.from_rx_data(data)

    assert packet is not None
    assert packet.opcode == BoksHistoryEvent.NFC_OPENING
    assert packet.extra_data["tag_type"] == 0x01
    assert packet.extra_data["tag_uid"] == "A1B2C3D4"
