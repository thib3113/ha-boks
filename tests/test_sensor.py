"""Test Boks sensors."""
from unittest.mock import AsyncMock
from homeassistant.core import HomeAssistant

async def test_sensors(hass: HomeAssistant, mock_boks_ble_device, mock_bluetooth, mock_config_entry) -> None:
    """Test that sensors are created and updated."""
    
    # Mock valid data from BLE
    mock_boks_ble_device.get_battery_level = AsyncMock(return_value=85)
    mock_boks_ble_device.get_battery_stats = AsyncMock(return_value={
        "format": "measures-first-min-mean-max-last",
        "temperature": 25
    })
    mock_boks_ble_device.get_code_counts = AsyncMock(return_value={"master": 1, "single_use": 2})
    mock_boks_ble_device.get_device_information = AsyncMock(return_value={
        "manufacturer_name": "Boks",
        "model_number": "Boks ONE",
        "software_revision": "4.5.1",
        "hardware_revision": "v2"
    })
    
    # Create Config Entry
    entry = mock_config_entry
    entry.add_to_hass(hass)

    # Setup integration
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Verify Battery Sensor
    battery_sensor = hass.states.get("sensor.boks_aa_bb_cc_dd_ee_ff_battery")
    assert battery_sensor is not None
    assert battery_sensor.state == "85"
    
    # Verify Code Count Sensors
    master_code_sensor = hass.states.get("sensor.boks_aa_bb_cc_dd_ee_ff_master_codes")
    assert master_code_sensor is not None
    assert master_code_sensor.state == "1"
    
    single_use_sensor = hass.states.get("sensor.boks_aa_bb_cc_dd_ee_ff_single_use_codes")
    assert single_use_sensor is not None
    assert single_use_sensor.state == "2"

    # Verify Last Event Sensor
    # Initially unknown or empty
    last_event_sensor = hass.states.get("sensor.boks_aa_bb_cc_dd_ee_ff_last_event")
    assert last_event_sensor is not None
