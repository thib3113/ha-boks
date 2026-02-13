# Boks Update System

The Boks devices are based on **nRF52** chips. The update system is designed to be **protected**.

If a user sends a fake or invalid update packet, the Boks will refuse to install it. Therefore, there is very little risk involved in installing an update ZIP file found on the internet.

## ⚠️ Important Note for "Non-NFC Boks" (V3 / nRF52811)

For the **Non-NFC Boks** (also known as Boks V3, running on nRF52811), please be aware of the following behavior:

*   **An invalid update will delete the previous software.**
*   Consequently, the Boks will remain in a state waiting for a valid software update and **will never restart** on the old version.

This behavior is different from the **NFC Boks** (V4 / nRF52833), which will safely restart on its previous software if an update fails.
