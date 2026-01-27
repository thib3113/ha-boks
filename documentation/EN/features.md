# Features of Boks Home Assistant Integration

This document details the features provided by the Boks Home Assistant integration.

## Basic Features (Available with Master Code only)

These features are accessible as soon as the Master Code (PIN) is configured.

### 🔓 Access Control
*   **Lock Entity**: Unlock your Boks directly from Home Assistant.

### 📊 Monitoring & Sensors
*   **Battery Level**: Monitor the device battery status.
*   **Battery Temperature**: Monitor the device battery temperature.
*   **Code Counts**: View how many codes (Master, Single-use) are stored on the box.
*   **Log Count**: View how many logs are stored on the box.
*   **Last Connection**: View the timestamp of the last successful connection to the device.
*   **Last Event**: View the most recent event from the device.
*   **Maintenance Status**: View the status of maintenance operations.
*   **Battery Format**: View the battery measurement format used by the device.
*   **Battery Type**: View the type of battery installed in the device.
*   **Battery Diagnostic Sensors**: View detailed battery voltage measurements (availability depends on battery format).

### 📜 Logging (History)
The integration automatically retrieves the Boks history and emits events (`event.boks_log_entry`):
*   Openings (Bluetooth, Keypad, Key)
*   Closings
*   Errors and invalid attempts

### 📦 Parcel Tracking (Manual Mode)
The `todo.parcels` entity is available to list expected parcels.
*   **Without Config Key**: You must manage codes manually (create the code on the box, then add it to the task description).
*   The integration will still validate the task if it sees this code used in the logs.

---

## Advanced Features (Requires Configuration Key)

These features require the **Configuration Key** (8 characters) to be set.

### ✨ Automatic Code Management
This is the true power of the integration.

*   **Automatic Generation**: Add a task "Amazon Package" to the Todo List, and the integration will **automatically create** a unique PIN code on the Boks and add it to the task description.

### 💳 NFC Management
*Requires Boks Model 4.0 or higher and firmware 4.3.3+.*

If your Boks is equipped with an NFC reader, you can manage your badges directly.

*   **Scan and Discovery**: Start the `boks.nfc_scan_start` service. The device enters listening mode for **20 seconds**. Present an unknown badge to receive a Home Assistant notification containing its UID.
*   **Registering Badges**: Add badges to the Boks whitelist using the `boks.nfc_register_tag` service.
*   **HA Tag Registry Integration**: The integration is coupled with Home Assistant's native tag registry. If you name a badge in HA, its name will automatically appear in the opening logs instead of the technical UID.
*   **Vigik Support**: The integration natively recognizes and distinguishes openings by **La Poste** (French Post) or other tertiary Vigik access tags.

### 🧩 Browser Extension
Using the [Boks Web Extension](https://github.com/thib3113/ha-boks-webextension) streamlines your checkout process:
1.  You are on a merchant site (e.g., Amazon), in the "Access Code" or "Delivery Instructions" field.
2.  **Right-click** in the text field -> select **"Generate a Boks Code"**.
3.  Enter a description (e.g., "Book Delivery").
4.  The extension communicates with Home Assistant to generate the code and automatically inserts it into the text field.

