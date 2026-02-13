# Boks Update System

The Boks devices are based on **nRF52** chips. The update system is designed to be **protected**.

If a user sends a fake or invalid update packet, the Boks will refuse to install it. Therefore, there is very little risk involved in installing an update ZIP file found on the internet.

## ⚠️ Important Note for "Non-NFC Boks" (V3 / nRF52811)

For the **Non-NFC Boks** (also known as Boks V3, running on nRF52811), please be aware of the following behavior:

*   **An invalid update will delete the previous software.**
*   Consequently, the Boks will remain in a state waiting for a valid software update and **will never restart** on the old version.

This behavior is different from the **NFC Boks** (V4 / nRF52833), which will safely restart on its previous software if an update fails.

## Update Process via Home Assistant Integration

The integration simplifies the update process by generating a dedicated web page for flashing your Boks device.

### 1. Accessing the Update Page
When an update is prepared, the integration generates a webpage accessible at:
`http://<your-home-assistant-ip>:<port>/local/boks/index.html`

*(Note: Replace `<your-home-assistant-ip>` with your Home Assistant's local IP address or domain name)*

### 2. Performing the Update
*   Open this page on a device with **Bluetooth capabilities** (smartphone, laptop).
*   Ensure you are **physically close** to your Boks.
*   Follow the on-screen instructions to connect and flash the new firmware.

### 3. Offline Locations (No Network Coverage)
The update page requires a connection to your Home Assistant instance to load.

**If your Boks is located in an area with no network coverage (e.g., basement with no WiFi/4G):**

1.  **Download the Firmware ZIP:** Before going to the Boks location, access the update page and download the firmware `.zip` file (usually available via a link on the page or at `/local/boks/v<version>/firmware.zip`).
2.  **Use a Mobile App:** Install the **nRF Connect for Mobile** app (available on Android and iOS).
3.  **Flash Manually:** Use the nRF Connect app to connect to your Boks and upload the downloaded `.zip` file manually.

### 4. "Cached Page" Mode (Two-Step Process)
Alternatively, you can use the web page even if you don't have internet access *at the Boks location*, without needing the nRF Connect app.

1.  **Step 1 (Online):** Open the update page (`/local/boks/index.html`) on your smartphone while you are **connected to WiFi** (or have 4G).
    *   The page will automatically download the firmware file and store it in your browser's memory (cache).
    *   Wait until the page is fully loaded.
2.  **Step 2 (Offline):** **Do not close the tab.** Walk to your Boks (even if you lose WiFi/4G connection).
3.  **Step 3 (Flash):** Since the firmware is already loaded in the page, you can click "Connect" and perform the update as if you were online.
