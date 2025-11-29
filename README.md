# Home Assistant Boks Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Validate Integration](https://github.com/thib3113/ha-boks/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/thib3113/ha-boks/actions/workflows/hassfest.yaml)
[![Validate HACS](https://github.com/thib3113/ha-boks/actions/workflows/hacs.yaml/badge.svg)](https://github.com/thib3113/ha-boks/actions/workflows/hacs.yaml)

## Description

This is a custom integration for **Home Assistant** that allows you to control and monitor your **Boks** connected parcel box via **Bluetooth Low Energy (BLE)**.

It allows you to open your Boks directly from Home Assistant without needing the official mobile app or an internet connection (once configured), leveraging Home Assistant's Bluetooth capabilities (local adapter or ESPHome proxies).

> [!WARNING]
> **Unofficial Integration**: This project is not affiliated with, endorsed by, or supported by Boks. Use it at your own risk.

## Features

*   **Lock Entity**: Unlock your Boks directly from the dashboard.
    *   Uses your stored **Master Code** by default.
    *   *Smart Fallback*: If you provided a Config Key but no Master Code, it attempts to generate a temporary single-use code on the fly.
*   **Sensors**:
    *   **Battery Level**: Monitors the device battery.
    *   **Code Counts** *(Admin only)*: Tracks the number of Master, Standard, and Multi-use codes stored on the device (requires Config Key).
*   **Events**: 
    *   Exposes an `event` entity (e.g., `event.boks_logs`) that reports history logs (openings, errors, etc.) retrieved from the device.

## Prerequisites

1.  **Hardware**:
    *   A Boks device.
    *   A Home Assistant server with a working Bluetooth adapter **OR** an ESPHome Bluetooth Proxy near the Boks.
2.  **Credentials**:
    *   **Master Code (Required)**: The 6-character PIN code you use to open the door (e.g., `1234AB`).
    *   **Credential (Optional)**: To enable advanced features (reading logs, counting codes), you need the **Configuration Key** (8 hex characters) or the **Master Key** (64 hex characters). These can be retrieved from your account data or during the initial provisioning process.

## Installation

[![Open your Home Assistant instance and open a repository in the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=thib3113&repository=ha-boks&category=Integration)
[![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=boks)

### Option 1: via HACS (Recommended)

1.  Open HACS in Home Assistant.
2.  Go to "Integrations".
3.  Click the 3 dots in the top right corner -> "Custom repositories".
4.  Add the URL of this repository.
5.  Select "Integration" as the category.
6.  Click "Add".
7.  Search for "Boks" and click "Download".
8.  Restart Home Assistant.

### Option 2: Manual

1.  Download the `boks.zip` file from the latest release.
2.  Unzip it.
3.  Copy the `boks` folder into your Home Assistant `custom_components/` directory.
4.  Restart Home Assistant.

## Configuration

1.  Go to **Settings** -> **Devices & Services**.
2.  Click **Add Integration**.
3.  Search for **Boks**.
4.  The integration should automatically discover your Boks if it is within range. Click on it.
5.  **Setup**:
    *   **Master Code**: Enter your unlock code (0-9, A, B).
    *   **Credential (Optional)**: Enter your Config Key (8 chars) or Master Key (64 hex characters) if you want to enable logs and admin sensors.
        *   *Future Proofing*: Providing the **Master Key** (64 hex chars) will likely allow for **offline code generation** in future versions of this integration, although it currently provides the same features as the Config Key.

## Events & Automations

The integration exposes an `event` entity (e.g., `event.boks_logs`) that fires when new logs are retrieved from the Boks device.

### Automation Trigger

You can use the "Event" trigger in Home Assistant automations to react to specific log events.

**Available Event Types:**

*   `door_opened`: Door Opened
*   `door_closed`: Door Closed
*   `code_ble_valid`: Valid BLE Code Used
*   `code_key_valid`: Valid Keypad Code Used
*   `code_ble_invalid`: Invalid BLE Code Used
*   `code_key_invalid`: Invalid Keypad Code Used
*   `error`: System Error
*   ... and more (battery tests, reboots, etc.)

### Example Automation

```yaml
alias: Notify when Boks door is opened
description: ""
trigger:
  - platform: state
    entity_id:
      - event.boks_logs
    attribute: event_type
    to: door_opened
condition: []
action:
  - service: notify.mobile_app_iphone
    data:
      message: "Your Boks has been opened!"
mode: single
```

## Debugging

To enable debug logging, add the following to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.boks: debug
```

## ⚖️ Legal Notice

> **⚠️ Disclaimer:** This is an unofficial project developed for **interoperability purposes only**.
> It is not affiliated with the device manufacturer. No proprietary code or assets are distributed here.
>
> 👉 Please read the full **[Legal Disclaimer & Reverse Engineering Notice](LEGALS.md)** before using this software.
