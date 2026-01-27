# Create a DIY Boks User Tag

This guide explains how to transform a standard NFC tag into a "User Tag" compatible with your Boks, allowing you to open the door via the NFC reader.

## Prerequisites

1.  **A Blank NFC Tag:**
    *   Type: **Mifare Classic 1K** (4-byte UID).
    *   *Note:* No need for a "Magic" tag (changeable UID) unless you want to clone an existing tag. A standard Mifare tag costs around $1/1€.
2.  **An Android Smartphone with NFC.**
3.  **The App:** [Mifare Classic Tool (MCT)](https://play.google.com/store/apps/details?id=de.syss.MifareClassicTool).

---

## The Technique

The Boks doesn't read just any tag. To be detected, the tag must have a **specific key** on its **Sector 1**. Without this key, the Boks will ignore the tag.

*   **Key A (Sector 1):** `873D9EF6C1A0`

---

## Step-by-Step Procedure (with MCT)

### Step 1: Add the Key to MCT

1.  Launch **Mifare Classic Tool**.
2.  Go to **"Edit/Analyze Key File"**.
3.  Open the `std.keys` file (or create a new one).
4.  Add a new line with the following key:
    `873D9EF6C1A0`
5.  Press the **Floppy Disk** icon to save.

### Step 2: Write the Key to the Tag

1.  Return to the main menu and choose **"Write Tag"**.
2.  Select the **"Write Block"** mode.
3.  In the **Block Number** field, enter: **`7`**.
    *   *Why 7?* This is the last block of Sector 1, which contains the access keys.
4.  In the **Data (Hex)** field, copy-paste exactly this:
    `873D9EF6C1A07F078840FFFFFFFFFFFF`
    *   `873D9EF6C1A0`: Key A (User Scan).
    *   `7F078840`: Permissions (Access Bits).
    *   `FFFFFFFFFFFF`: Key B (Default).
5.  Place your blank tag on the back of your phone.
6.  Press **"Write Block"**.
7.  MCT will ask which keys to use to access the tag ("Map Keys to Sectors").
    *   Select the `std.keys` file (which should contain `FFFFFFFFFFFF`, the default key for blank tags).
    *   Start the mapping/writing process.
8.  Confirm the warning ("Writing to Sector Trailer...").

### Step 3: Verify the Tag

1.  Return to the main menu -> **"Read Tag"**.
2.  Scan your tag.
3.  Check **Sector 1**:
    *   **Block 5** (the second one in sector 1) should be empty (all `00` or `FF`, but definitely **not** starting with `AA 07`).
    *   If block 5 contains `AA 07`, erase it (write `00` to block 5 via "Write Block"), otherwise the Boks will think it's a La Poste/Vigik system tag!

---

## Usage with Home Assistant

Once your tag is prepared:

1.  In Home Assistant, go to **Developer Tools** -> **Services**.
2.  Call the `boks.nfc_scan_start` service.
3.  Place your tag on the Boks (blue LED flashes).
4.  You should receive a "Boks NFC Tag Discovered" notification with the tag's UID (e.g., `A1B2C3D4`).
5.  Use the `boks.nfc_register_tag` service with this UID and a name (e.g., "Dad's Tag") to add it.
6.  You're done! Your tag now opens the door.
