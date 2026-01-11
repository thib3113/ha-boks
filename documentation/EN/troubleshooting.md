# Troubleshooting Boks Home Assistant Integration

This document provides guidance on how to troubleshoot common issues and enable debug logging for the Boks Home Assistant integration.

## Enabling Debug Logging

> **⚠️ Security Warning:** Enabling debug logging will expose sensitive information in your Home Assistant logs. **Before sharing logs publicly**, please enable the **"Anonymize logs"** option in the integration settings. This will automatically replace your private keys and PIN codes with fake values (e.g., `1234AB`, `1A3B5C7E`).

When encountering issues with the Boks integration, enabling debug logging can provide valuable insights into its operation and help identify the root cause of problems.

To enable debug logging, add the following configuration to your Home Assistant `configuration.yaml` file:

```yaml
logger:
  default: info
  logs:
    custom_components.boks: debug
```

After adding this, restart your Home Assistant instance. Once restarted, check your Home Assistant logs (typically `home-assistant.log` in your configuration directory) for messages prefixed with `custom_components.boks`. These logs will contain detailed information about the integration's activities, including Bluetooth communication, command sending, and responses.

## Common Issues and Solutions

### 1. Boks device not discovered

*   **Check Bluetooth**: Ensure Bluetooth is enabled and working on your Home Assistant server or ESPHome proxy. Verify other Bluetooth devices are discoverable.
*   **Range**: Make sure your Boks device is within close proximity to your Home Assistant Bluetooth adapter or ESPHome proxy. Bluetooth range can be limited.
*   **ESPHome Proxy**: If using an ESPHome proxy, ensure it is properly configured and connected to Home Assistant. Check its logs for Bluetooth-related errors.
*   **Restart Integration/Home Assistant**: Sometimes a simple restart of the Boks integration (from Devices & Services -> Boks -> Reload) or Home Assistant itself can resolve discovery issues. If battery entities are not displaying correctly, try restarting the integration.

### 2. Unable to connect or control Boks

*   **Master Code/Credential**: Double-check that the Master Code and any optional Credential (Configuration Key/Master Key) are entered correctly in the integration configuration. Typos are common.
*   **Boks Status**: Ensure your Boks device is powered on and its Bluetooth is active.
*   **Other Connections**: Make sure no other device (e.g., the official Boks mobile app) is currently connected to your Boks via Bluetooth, as this can prevent Home Assistant from connecting.
*   **Interference**: Minimize potential Bluetooth interference from other devices.

### 3. Features not working (e.g., no logs, no code counts)

*   **Credential Provided**: These features require a Configuration Key or Master Key to be provided during configuration. If you did not provide one, or provided an incorrect one, these features will not function.
*   **Permissions**: Ensure the provided Credential has the necessary permissions for the Boks device.
*   **Device Firmware**: Very old Boks firmware might not support certain features or logging mechanisms. Ensure your Boks firmware is up to date if possible.

### 4. Battery diagnostic sensors not showing detailed information

*   **Battery Format**: The detailed battery diagnostic sensors (e.g., min, max, mean voltage) are only available when the Boks device supports the appropriate battery measurement format. Some devices may only support basic battery level reporting.
*   **First Door Opening**: Battery format information is detected during the first door opening of the device. If the sensors are not showing detailed information, try opening the Boks door, then restart the integration to force a reconnection and redetection of the battery format.
*   **Device Compatibility**: Older Boks devices may not support advanced battery diagnostics. Check your device's hardware version to determine its capabilities.

### 5. Integration becoming unavailable or disconnected

*   **Bluetooth Stability**: Bluetooth connections can sometimes be unstable. Ensure your Bluetooth hardware is reliable.
*   **Distance/Obstructions**: Too much distance or physical obstructions (walls, metal) between your Home Assistant Bluetooth adapter/proxy and the Boks can lead to disconnections.
*   **Battery Level**: A low battery in your Boks device can affect Bluetooth connectivity. Check the battery level sensor.

### 6. Door won't close properly after opening multiple times quickly

**Q:** "I opened the door too quickly twice (either with this app or multiple apps), and it refuses to close?"

**A:** "You need to keep the door closed, then enter a permanent code (master code in English), the lock will restart its complete cycle, and then you should be able to close it properly."

If you continue to experience issues after following these steps and reviewing debug logs, please open an issue on the [GitHub repository](https://github.com/thib3113/ha-boks/issues), providing your debug logs (sanitized of sensitive information) and a detailed description of the problem.
