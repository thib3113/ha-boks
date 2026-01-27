"""Test for NfcScanResultPacket."""
from custom_components.boks.packets.rx.nfc_scan_result import NfcScanResultPacket
from custom_components.boks.ble.const import BoksNotificationOpcode

def test_parse_nfc_scan_result():
    # 1. FOUND
    opcode = BoksNotificationOpcode.NOTIFY_NFC_TAG_FOUND
    uid_hex = "112233"
    uid_bytes = bytes.fromhex(uid_hex)
    
    raw_data = bytearray()
    raw_data.append(opcode)
    raw_data.append(1 + len(uid_bytes))
    raw_data.append(len(uid_bytes))
    raw_data.extend(uid_bytes)
    checksum = sum(raw_data) & 0xFF
    raw_data.append(checksum)
    
    packet = NfcScanResultPacket(opcode, raw_data)
    assert packet.status == "found"
    assert packet.uid == uid_hex
    assert packet.verify_checksum()
    
    # 2. ALREADY EXISTS
    opcode = BoksNotificationOpcode.ERROR_NFC_TAG_ALREADY_EXISTS_SCAN
    
    raw_data = bytearray()
    raw_data.append(opcode)
    raw_data.append(1 + len(uid_bytes))
    raw_data.append(len(uid_bytes))
    raw_data.extend(uid_bytes)
    checksum = sum(raw_data) & 0xFF
    raw_data.append(checksum)
    
    packet = NfcScanResultPacket(opcode, raw_data)
    assert packet.status == "already_exists"
    assert packet.uid == uid_hex
    assert packet.verify_checksum()
    
    # 3. TIMEOUT
    opcode = BoksNotificationOpcode.ERROR_NFC_SCAN_TIMEOUT
    raw_data = bytearray([opcode, 0x00, opcode]) # No payload
    
    packet = NfcScanResultPacket(opcode, raw_data)
    assert packet.status == "timeout"
    assert packet.uid is None
    assert packet.verify_checksum()
