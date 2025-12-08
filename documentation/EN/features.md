# Features of Boks Home Assistant Integration

This document details the features provided by the Boks Home Assistant integration.

## Basic Features (Available with Master Code only)

These features are accessible as soon as the Master Code (PIN) is configured.

### 🔓 Access Control
*   **Lock Entity**: Unlock your Boks directly from Home Assistant.

### 📊 Monitoring & Sensors
*   **Battery Level**: Monitor the device battery status.
*   **Code Counts**: View how many codes (Master, Standard, Multi-use) are stored on the box.

### 📜 Logging (History)
The integration automatically retrieves the Boks history and emits events (`event.boks_logs`):
*   Openings (Bluetooth, Keypad, Key)
*   Closings
*   Errors and invalid attempts

### 📦 Parcel Tracking (Manual Mode)
The `todo.suivi_boks` entity is available to list expected parcels.
*   **Without Config Key**: You must manage codes manually (create the code on the box, then add it to the task description).
*   The integration will still validate the task if it sees this code used in the logs.

---

## Advanced Features (Requires Configuration Key)

These features require the **Configuration Key** (8 characters) to be set.

### ✨ Automatic Code Management
This is the true power of the integration.

*   **Automatic Generation**: Add a task "Amazon Package" to the Todo List, and the integration will **automatically create** a unique PIN code on the Boks and add it to the task description.

### 🧩 Browser Extension
Using the [Boks Web Extension](https://github.com/thib3113/ha-boks-webextension) streamlines your checkout process:
1.  You are on a merchant site (e.g., Amazon), in the "Access Code" or "Delivery Instructions" field.
2.  **Right-click** in the text field -> select **"Generate a Boks Code"**.
3.  Enter a description (e.g., "Book Delivery").
4.  The extension communicates with Home Assistant to generate the code and automatically inserts it into the text field.

