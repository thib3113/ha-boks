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

**⚠️ Note on application blocking:**
This method uses the same servers as the official application.
*   If your account is blocked in the application (awaiting migration), the script will **not** be able to retrieve the key (it will appear empty).
*   This method only works if your account has been migrated.

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

## Method 3: Manual Extraction (iOS - Advanced)

If you have an iPhone and have used the Boks app on it, you can extract the key from a backup.

### 1. Retrieve Data

**Prerequisites:**
*   A computer (Windows or Mac).
*   **iMazing** (the free version allows creating backups).
*   **iBackupBot** (or any other iOS backup explorer like iExplorer).

**Steps:**
1.  **Backup**: Create an **unencrypted** local backup using iMazing. *It is essential that encryption is disabled to access the files.*
2.  **Navigation**: Use iBackupBot to browse the backup and go to:
    `User App Files` > `com.boks.app` > `Library` > `WebKit` > `WebsiteData` > `Default` > `IndexedDB`.
3.  **Target**: Identify the folder containing the largest database (around 120 KB) and locate the `IndexedDB.sqlite3` file.
4.  **Export**: Extract this file to your computer.

### 2. Analyze Data

**Automated Method (iOS 15+):**
WebKit uses a specific SQLite format starting from iOS 15, which is handled by the **dfindexeddb** tool.

1.  Install the tool: `pip install dfindexeddb`
2.  Run the analysis:
    ```bash
    dfindexeddb db -s IndexedDB.sqlite3 --format safari
    ```
3.  Search for `"configurationKey"` in the JSON output.

**Fallback Method (iOS 14 or lower):**
If the script returns a `ParserError: 10 is not the expected CurrentVersion` error, the WebKit version is older.

1.  Open the `IndexedDB.sqlite3` file with a hex editor (e.g., **WinHex**, **Hex Fiend**).
2.  Search for the ANSI string `configurationKey`.
3.  The key is located right after one of the occurrences.
    *   *Note: The encoding might be UTF-16 (a `00` byte between each character).*

## What to do if no method works? (Last resort)

If Method 1 (Cloud) returns an error or an empty key, and you don't have a local backup (Methods 2 & 3), here are the likely causes and solutions:

### 1. Your account is not "Migrated"
Boks has imposed a paid migration to continue using their Cloud services. If you haven't paid for this migration, the Cloud API will not return your `Configuration Key`.
*   **Verification**: Open the official Boks app. If it asks you to pay to access your boks or if your boks no longer appear, you have not migrated.
*   **Solution**: You must perform this migration at least once to unlock official API access and allow the retrieval script to work.

### 2. The key hasn't been "pushed" to the Cloud
Sometimes, even with a migrated account, the API doesn't return the key if no recent action has "forced" its synchronization.
*   **Tip**: In the official app, create a **new permanent code** (you can delete it right after). This action often forces the app to synchronize security keys with the server. Then, run the **Method 1** script again.

### Why make this effort? (Total Independence)
Once you have retrieved this **Configuration Key** (8 characters):
1.  **Save it securely.**
2.  **Become independent**: You will **never again** need the Boks servers (just in case the company goes bankrupt, once again...) or the official app to control your Boks. This key allows you to use any third-party application (like this Home Assistant integration) to generate codes and communicate directly via Bluetooth.
