"""Tests for the Boks battery diagnostics sensors."""
from unittest.mock import MagicMock, patch

import pytest
from custom_components.boks.coordinator import BoksDataUpdateCoordinator
from custom_components.boks.sensors.diagnostics.battery_diagnostic_sensor import BoksBatteryDiagnosticSensor
from custom_components.boks.sensors.diagnostics.battery_format_sensor import BoksBatteryFormatSensor
from custom_components.boks.sensors.diagnostics.battery_type_sensor import BoksBatteryTypeSensor
from homeassistant.config_entries import ConfigEntry


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock(spec=BoksDataUpdateCoordinator)
    coordinator.data = {}
    return coordinator


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.data = {"address": "AA:BB:CC:DD:EE:FF"}
    return entry


def test_battery_diagnostic_sensor_init(mock_coordinator, mock_config_entry):
    """Test battery diagnostic sensor initialization."""
    sensor = BoksBatteryDiagnosticSensor(mock_coordinator, mock_config_entry, "level_single")

    assert sensor._key == "level_single"
    assert sensor._attr_translation_key == "battery_level_single"
    assert sensor._attr_unique_id == "AA:BB:CC:DD:EE:FF_battery_level_single"
    assert sensor.suggested_object_id == "battery_level_single"


def test_battery_diagnostic_sensor_get_current_value_with_data(mock_coordinator, mock_config_entry):
    """Test getting current value with valid data."""
    mock_coordinator.data = {
        "battery_stats": {
            "format": "measure-single",
            "level_single": 85,
            "temperature": 25
        }
    }

    sensor = BoksBatteryDiagnosticSensor(mock_coordinator, mock_config_entry, "level_single")
    value = sensor._get_current_value()

    assert value == 8.5  # Should be divided by 10


def test_battery_diagnostic_sensor_get_current_value_temperature(mock_coordinator, mock_config_entry):
    """Test getting temperature value."""
    mock_coordinator.data = {
        "battery_stats": {
            "format": "measure-single",
            "level_single": 85,
            "temperature": 25
        }
    }

    sensor = BoksBatteryDiagnosticSensor(mock_coordinator, mock_config_entry, "temperature")
    value = sensor._get_current_value()

    assert value == 25.0  # Temperature should not be divided


def test_battery_diagnostic_sensor_get_current_value_no_data(mock_coordinator, mock_config_entry):
    """Test getting current value with no data."""
    mock_coordinator.data = {}

    sensor = BoksBatteryDiagnosticSensor(mock_coordinator, mock_config_entry, "level_single")
    value = sensor._get_current_value()

    assert value is None


def test_battery_diagnostic_sensor_available_with_data(mock_coordinator, mock_config_entry):
    """Test sensor availability with data."""
    mock_coordinator.data = {
        "battery_stats": {
            "format": "measure-single"
        }
    }

    sensor = BoksBatteryDiagnosticSensor(mock_coordinator, mock_config_entry, "level_single")
    available = sensor.available

    assert available is True


def test_battery_diagnostic_sensor_available_with_wrong_format(mock_coordinator, mock_config_entry):
    """Test sensor availability with wrong format."""
    mock_coordinator.data = {
        "battery_stats": {
            "format": "measures-t1-t5-t10"
        }
    }

    sensor = BoksBatteryDiagnosticSensor(mock_coordinator, mock_config_entry, "level_single")
    available = sensor.available

    assert available is False


def test_battery_format_sensor_init(mock_coordinator, mock_config_entry):
    """Test battery format sensor initialization."""
    sensor = BoksBatteryFormatSensor(mock_coordinator, mock_config_entry)

    assert sensor._attr_translation_key == "battery_format"
    assert sensor._attr_unique_id == "AA:BB:CC:DD:EE:FF_battery_format"
    assert sensor.suggested_object_id == "battery_format"


def test_battery_format_sensor_get_current_value_with_data(mock_coordinator, mock_config_entry):
    """Test getting current format value with valid data."""
    mock_coordinator.data = {
        "battery_stats": {
            "format": "measure-single"
        }
    }

    sensor = BoksBatteryFormatSensor(mock_coordinator, mock_config_entry)
    value = sensor._get_current_value()

    assert value == "measure-single"


def test_battery_format_sensor_get_current_value_with_unknown_format(mock_coordinator, mock_config_entry):
    """Test getting current format value with unknown format."""
    mock_coordinator.data = {
        "battery_stats": {
            "format": None
        }
    }

    sensor = BoksBatteryFormatSensor(mock_coordinator, mock_config_entry)
    value = sensor._get_current_value()

    assert value == "unknown"


def test_battery_type_sensor_init(mock_coordinator, mock_config_entry):
    """Test battery type sensor initialization."""
    sensor = BoksBatteryTypeSensor(mock_coordinator, mock_config_entry)

    assert sensor._attr_translation_key == "battery_type"
    assert sensor._attr_unique_id == "AA:BB:CC:DD:EE:FF_battery_type"
    assert sensor.suggested_object_id == "battery_type"


def test_battery_type_sensor_get_current_value_with_data(mock_coordinator, mock_config_entry):
    """Test getting current type value with valid data."""
    # Mock BOKS_HARDWARE_INFO behavior
    # if hw_version == "3.0": return "lsh14"
    # if hw_version == "4.0": return "8x_aaa"

    # Patch BOKS_HARDWARE_INFO in the sensor module
    with patch("custom_components.boks.sensors.diagnostics.battery_type_sensor.BOKS_HARDWARE_INFO", {"1.0.0": {"hw_version": "3.0"}}):
        mock_coordinator.data = {
            "device_info_service": {
                "firmware_revision": "1.0.0"
            }
        }
        sensor = BoksBatteryTypeSensor(mock_coordinator, mock_config_entry)
        value = sensor._get_current_value()

        assert value == "lsh14"


def test_battery_type_sensor_get_current_value_with_unknown_type(mock_coordinator, mock_config_entry):
    """Test getting current type value with unknown type."""
    mock_coordinator.data = {
        "device_info_service": {
            "firmware_revision": "unknown_fw"
        }
    }

    sensor = BoksBatteryTypeSensor(mock_coordinator, mock_config_entry)
    value = sensor._get_current_value()

    assert value == "unknown"
