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

**No external application is required.** The web page handles everything, even if your Boks is in a location without internet coverage (e.g., a basement).

### Standard Workflow (Works Offline)

The update process is designed to work in two steps to accommodate Boks located in "dead zones" (no WiFi/4G):

1.  **Step 1: Preparation (Online)**
    *   Ideally, stay at home connected to your **WiFi**.
    *   Open the update page link provided by the integration:
        `http://<your-home-assistant-ip>:<port>/local/boks/index.html`
    *   **Compatibility Note:** If your connection is not secure (HTTP) or if you are using an iPhone/iPad, the page will automatically detect it and provide a link to a secure online tool that can perform the update for you.
    *   **Wait for the page to load completely.** The firmware file is automatically downloaded and stored in your browser's memory.
    *   *Do not close the tab.*

2.  **Step 2: Flashing (At the Boks)**
    *   Walk to your Boks location. **You do not need an internet connection anymore.**
    *   Ensure Bluetooth is enabled on your device.
    *   Click the **"Connect"** button on the page.
    *   Select your Boks device from the list.
    *   Follow the on-screen instructions to start the update.

### Troubleshooting / Manual Fallback

If you are unable to use the web interface (e.g., incompatible browser or iOS restrictions), you can perform a manual update:

1.  **Download the Firmware ZIP:** On the update page, look for the download link to get the firmware `.zip` file.
2.  **Use nRF Connect:** Install the **nRF Connect for Mobile** app (Android/iOS).
3.  **Flash Manually:** Use the app to connect to your Boks and upload the `.zip` file.
