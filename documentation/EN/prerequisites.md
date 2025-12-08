# Prerequisites for Boks Home Assistant Integration

Before installing and configuring the Boks Home Assistant integration, ensure you meet the following prerequisites.

## Hardware Requirements

1.  **A Boks device**: You must own a Boks connected parcel box.
2.  **Home Assistant Bluetooth Integration with an Active Relay**:
    To control your Boks (unlock, retrieve logs), Home Assistant must be able to establish an **active connection** with the device. Passive listening (passive scanning) is not sufficient.

    This can be achieved through:
    *   **A local Bluetooth adapter**: Plugged directly into the machine (USB or built-in, e.g., Raspberry Pi). These typically support active connections by default.
    *   **An ESPHome Bluetooth Proxy (Recommended)**: Ideal if your Boks is far from your server.
        *   ⚠️ **Important**: The proxy must be in **ACTIVE** mode. This is usually the default (`active: true`), but check your configuration.
        *   See the **[ESPHome documentation](https://esphome.io/components/bluetooth_proxy/)**.
    *   ❌ **Shelly (Warning)**: Most Shelly devices (Gen 2/3) used as Bluetooth proxies do **NOT** support active (GATT) connections.
        *   If you see the message *"This adapter does not support making active (GATT) connections"* in Home Assistant, it will **NOT work** for opening the Boks.
        *   They might work for presence or battery detection (passive), but not for unlocking.

    **Troubleshooting**:
    *   If your Boks is discovered but commands (unlocking) consistently fail, ensure your proxy supports active connections (prefer ESPHome or Local USB).

## Credential Requirements

To fully utilize the integration, you will need the following credentials:

1.  **Master Code (Required)**: This is the 6-character PIN code you typically use to manually open your Boks (e.g., `1234AB`). This code is essential for the basic unlock functionality.
2.  **Configuration Key (Strongly Recommended)**: Needed for advanced features (parcel management, code generation, logs).
    *   See the dedicated guide: **[How to Retrieve your Configuration Key](RETRIEVE_KEYS.md)**.
