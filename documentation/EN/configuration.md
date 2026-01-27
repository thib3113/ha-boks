# Configuration Guide for Boks Home Assistant Integration

This guide explains how to configure the Boks Home Assistant integration after it has been installed, with a focus on how different credential inputs enable various features.

## Initial Setup

1.  **Navigate to Integrations**: In your Home Assistant frontend, go to **Settings** -> **Devices & Services**.
2.  **Add Integration**: Click on the "Add Integration" button (usually a blue plus sign in the bottom right corner).
3.  **Search for Boks**: In the search bar, type "Boks" and select the integration.
4.  **Device Discovery**: The integration should automatically discover your Boks device if it is within Bluetooth range of your Home Assistant server or an ESPHome Bluetooth Proxy. Select the discovered Boks device.
5.  **Setup Form**: A configuration dialog will appear, prompting you for credentials. The level of detail you provide here determines the features available to you.

### Credential Tiers and Enabled Functionalities

The Boks integration offers a tiered approach to functionality based on the credentials you provide during setup:

*   **1. Master Code Only (Required for Basic Operation)**
    *   **Input**: Enter your 6-character Boks unlock code (e.g., `1234AB`) in the "Master Code" field. Leave the "Credential" field empty.
    *   **Features Enabled**:
        *   **Boks Unlock**: Control the `lock` entity to open your Boks.
        *   **Battery Level Sensor**: Monitor your Boks device's battery status (battery data is only available after opening the door). Note: Battery entities may require an integration restart to appear.
        *   **Code Counts Sensor**: Monitor the number of Master, Standard, and Multi-use codes stored on your device.
        *   **Event Logging**: Receive basic operational events from your Boks (e.g., door opened/closed, valid/invalid code attempts) via the `event.<name>_logs` entity.
        *   **Todo List (Basic Functionality)**: A `todo.<name>_parcels` entity will be created. You can use it to track parcels (with descriptions), but you will need to manually manage (create and associate) any PIN codes. The integration will still attempt to validate and mark tasks as complete if it detects a manually associated code in its logs and emit `boks_parcel_completed` events. In "Degraded Mode" (when no Config Key is provided), parcel tracking is available without code generation.

*   **2. Config Key or Master Key (Optional, Recommended for Advanced Features)**
    *   **Input**: In addition to your "Master Code," enter your **Configuration Key** (8 hex characters) or **Master Key** (64 hex characters) into the "Credential" field.
        *   *Tip:* Providing the **Master Key** is recommended as it offers more capabilities and may support future features such as offline code generation. Currently, both Config Key and Master Key enable the same set of advanced features.
    *   **Features Enabled**:
        *   **All Master Code Only Features**
        *   **Enhanced Todo List Integration (Parcel Management)**: The `todo.<name>_parcels` entity provides full functionality.
            *   **Automatic PIN Generation**: When you add an item to the `todo.<name>_parcels` list with a description (e.g., "Package from Amazon"), the integration will automatically generate a unique PIN code associated with that parcel entry.
            *   **Description Support**: You can add meaningful descriptions to your todo items, which are linked to the generated PINs.
            *   **User Responsibility for Modified PINs**: If you manually change an automatically generated PIN for a todo item, the integration will recognize the change but will no longer automatically manage that specific PIN. You become responsible for its management.
            *   **Automatic Task Completion & Event Emission**: The integration will automatically mark tasks as complete when it detects the associated code being used in its logs and will emit `boks_parcel_completed` events.

6.  **Submit**: Click "Submit" to complete the configuration and activate the integration with the selected features.

## System Options

Once the integration is installed, you can modify its options by clicking **Configure** on the Boks integration card (via Devices & Services).

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
3.  Adjust the settings as needed and save. This will update the available features based on the new credentials provided.
