# How to Retrieve your Configuration Key

To unlock the advanced features of the Boks integration (specifically **parcel management** and **code creation**), you need the **Configuration Key**.

> **Note:** This key is **NOT** required for basic usage (Opening the door, reading logs, battery level). The Master Code (PIN) is sufficient for that.

## What is the Configuration Key?

It is an 8-character hexadecimal string (e.g., `A1B2C3D4`).
Technically, it consists of the **last 8 characters** of the **Master Key** (a 64-character key).

> **About the Master Key:**
> The full Master Key (64 characters) can only be obtained during the Boks initialization (first pairing) or during a code "re-generation" procedure (which itself requires the previous Config Key).
>
> However, its value is currently very limited for Home Assistant, as the **Configuration Key** is sufficient to enable all advanced features (including code generation via the integration).

## Method 1: Via Cloud Script (Recommended)

A Python script is provided in the `scripts/` folder of this integration. It connects to your Boks account (via the cloud API) to retrieve your devices and their keys.

**Advantage:** No need for physical access to the Boks, Android device, or cables. Works with your Boks email and password.

### Prerequisites
1.  A computer with **Python 3** installed.
2.  The `requests` library installed (`pip install requests`).

### Steps

1.  Open a terminal in the integration folder.
2.  Navigate to the `scripts` folder and run the script:

```bash
cd scripts
python get_config_key.py
```

3.  Enter your Boks account **Email** and **Password** when prompted.
    *   *Privacy Note: Your credentials are used only for this session to query the Boks API. They are neither saved nor sent elsewhere.*
4.  The script will display a list of your Boks devices along with their **Configuration Keys**.

Copy the key (8 characters) and paste it into the Home Assistant integration configuration.

## Method 2: Manual Extraction (Android - Advanced)

If the Cloud method doesn't work, you can try retrieving the data from the Android application.

### 1. Retrieve Data
You need to obtain the application's database folder.
*   **Android Path**: `/data/user/0/com.boks.app/app_webview/Default/IndexedDB/`
*   **Constraints**: Since the app generally disables standard backup (`allowBackup=false`), a simple `adb backup` will not work.
    *   **Root**: If your phone is rooted, you can access the path above directly.
    *   **Manufacturer Tools**: Some proprietary backup tools (Samsung Smart Switch, Xiaomi Backup, OnePlus Switch, etc.) may sometimes bypass this restriction and include app data.
    *   Copy the extracted folder to your computer.

### 2. Analyze Data

**Quick Method (Might work):**
You can first try using the `strings` command (Linux/Mac) or a hex editor on the `.ldb` files to search for `"configurationKey"`.
If you are lucky (uncompressed data), you will find the key directly.

**Robust Method (Recommended if quick method fails):**
Since LevelDB often compresses data, the simple method might fail. In that case, use the specialized tool **[dfindexeddb](https://github.com/google/dfindexeddb)**:

1.  Install the tool: `pip install dfindexeddb`
2.  Analyze your folder:
    ```bash
    dfindexeddb db -s /path/to/your/IndexedDB/folder/ --format chrome --use_manifest
    ```
3.  Search for `"configurationKey"` in the output.

You should find a JSON structure containing:
`"configurationKey":"XXXXXXXX"`

This `XXXXXXXX` value (8 characters) is what you need.