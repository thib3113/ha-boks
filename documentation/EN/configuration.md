# Configuration Guide for Boks Home Assistant Integration

This guide explains how to configure the Boks Home Assistant integration after installation.

## Initial Setup

1.  **Navigate to Integrations**: In your Home Assistant frontend, go to **Settings** -> **Devices & Services**.
2.  **Add Integration**: Click on the "Add Integration" button (usually a blue plus sign in the bottom right corner).
3.  **Search for Boks**: In the search bar, type "Boks" and select the integration.
4.  **Device Discovery**: The integration should automatically discover your Boks device if it is within Bluetooth range of your Home Assistant server or an ESPHome Bluetooth Proxy. Select the discovered Boks device.
5.  **Setup Form**: A configuration dialog will appear.

### Credential Tiers

*   **Master Code Only**: Enter your 6-character PIN code. Enables basic unlocking, battery reading, and basic logs.
*   **Config/Master Key** (Recommended): Enables automatic code generation and advanced parcel management.

## System Options

Once the integration is installed, you can modify its options by clicking **Configure** on the Boks integration card.

### Available Settings

*   **Update Interval (minutes)** (`scan_interval`):
    *   Sets how often Home Assistant attempts to connect to the Boks to check its status (e.g., battery).
    *   *Note*: A frequency that is too high may reduce battery life.

*   **Full Refresh Interval (hours)** (`full_refresh_interval`):
    *   Sets the frequency for a full data synchronization (logs, deep configuration).

*   **Master Code for Opening (Optional)** (`master_code`):
    *   Allows you to change the default code used by the "Open" action (`lock.open`). Useful if you have manually changed the code on the device.

*   **Anonymize Logs** (`anonymize_logs`):
    *   **Crucial for Support**: If enabled, all PIN codes and sensitive identifiers will be replaced with dummy values (e.g., `1234AB`) in Home Assistant debug logs.
    *   Enable this option **before** sharing your logs for a support request or bug report.

## Advanced Configuration

### Battery Format Persistence

The Boks device supports different battery measurement formats, which are automatically detected by the integration:

*   **measure-single**: Simple battery level measurement (standard battery service)
*   **measures-t1-t5-t10**: Multiple measurements at different time intervals
*   **measures-first-min-mean-max-last**: Detailed measurements including min, mean, and max values

The integration automatically detects the battery format during the first door opening and stores it in the configuration. This ensures that the appropriate battery diagnostic sensors are created and available even when the device is offline. If the battery format changes (e.g., due to a firmware update), the integration will detect and update the stored format during the next door opening.

## Reconfiguring an Existing Integration

If you need to change the Master Code or Credential for an already configured Boks integration:

1.  Go to **Settings** -> **Devices & Services**.
2.  Find your Boks integration and click on "Configure".
3.  Adjust the settings as needed and save.
