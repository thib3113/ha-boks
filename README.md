<p align="center">
  <img src="images/icon.png" width="200" alt="Boks Logo">
</p>

# Home Assistant Boks Integration

> 🇫🇷 **[Lire la documentation en Français](documentation/FR/introduction.md)**

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub License](https://img.shields.io/github/license/thib3113/ha-boks?color=blue)](LICENSE)
[![Validate Integration](https://img.shields.io/github/actions/workflow/status/thib3113/ha-boks/hassfest.yaml)](https://github.com/thib3113/ha-boks/actions/workflows/hassfest.yaml)
[![Validate HACS](https://img.shields.io/github/actions/workflow/status/thib3113/ha-boks/hacs.yaml)](https://github.com/thib3113/ha-boks/actions/workflows/hacs.yaml)

## Table of Contents

*   [Description](#description)
*   [Features](#features)
*   [Prerequisites](#prerequisites)
*   [Installation](#installation)
*   [Configuration](#configuration)
*   [Events & Automations](#events--automations)
*   [Debugging](#debugging)
*   [Detailed Documentation](#detailed-documentation)
*   [Legal Notice](#legal-notice)

## Description

This is a custom integration for **Home Assistant** that allows you to control and monitor your **Boks** connected parcel box via **Bluetooth Low Energy (BLE)**.

It allows you to open your Boks directly from Home Assistant without needing the official mobile app or an internet connection (once configured), leveraging Home Assistant's Bluetooth capabilities (local adapter or ESPHome proxies).

## Features

*   **Lock Entity**: Unlock your Boks directly from the dashboard.
*   **Sensors**: Battery Level, Code Counts.
*   **Logs & History**: View openings, errors, and delivery history.
*   **Smart Parcel Tracking (To-Do List)**:
    *   **Auto-Generation (Requires Config Key)**: Automatically creates a PIN code for each delivery added to the list.
    *   **Auto-Completion**: Marks tasks as done when the code is used.
    *   **Web Extension**: Compatible with the **[Boks Web Extension](https://github.com/thib3113/ha-boks-webextension)**.

## Prerequisites

1.  **Hardware**:
    *   A Boks device.
    *   A Bluetooth Adapter (Local) OR ESPHome Proxy (**Active Mode** required).
    *   *Note: Most Shelly devices do not support active connections.*
2.  **Credentials**:
    *   **Master Code (Required)**: The 6-character PIN code (e.g., `1234AB`).
    *   **Configuration Key (Recommended)**: Required for **Automatic Code Generation**.
        *   [How to retrieve your Configuration Key](documentation/EN/RETRIEVE_KEYS.md).

## Installation

[![Open your Home Assistant instance and open a repository in the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=thib3113&repository=ha-boks&category=Integration)
[![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=boks)

### Option 1: via HACS (Recommended)

1.  Open HACS -> Integrations.
2.  Add Custom Repository: `thib3113/ha-boks` (Category: Integration).
3.  Search for "Boks" and Download.
4.  Restart Home Assistant.

### Option 2: Manual

1.  Download `boks.zip` from the latest release.
2.  Unzip into `custom_components/boks`.
3.  Restart Home Assistant.

## Configuration

1.  **Settings** -> **Devices & Services** -> **Add Integration** -> **Boks**.
2.  **Setup**:
    *   **Master Code**: Your unlock code.
    *   **Credential**: Your Configuration Key (for auto-code generation).

## Events & Automations

The integration exposes `event.boks_logs` for automations.

### Example Automation

```yaml
alias: Notify when Boks opened
trigger:
  - platform: state
    entity_id: event.boks_logs
condition:
  - condition: state
    entity_id: event.boks_logs
    attribute: event_type
    state: door_opened
action:
  - action: notify.mobile_app
    data:
      message: "Boks opened!"
```

## 📦 Smart Parcel Tracking

The integration creates a **To-Do List** entity.

### How it works (with Config Key)

1.  **Add a Task**: "Amazon Delivery".
2.  **Auto-Generation**: The integration creates a PIN code on the Boks and adds it to the task description.
3.  **Delivery**: Give this code to the carrier.
4.  **Auto-Completion**: When the code is used, the task is marked as done.

### 🧩 Browser Extension

Use the **[Home Assistant Boks Extension](https://github.com/thib3113/ha-boks-webextension)** to add parcels directly from merchant sites!
*   **Right-click** on any delivery instruction field -> **"Generate a Boks Code"**.
*   It automatically creates the code in Home Assistant and fills the field for you.


## Debugging

> **⚠️ Security Warning:** Enabling debug logging will expose sensitive information in your Home Assistant logs. **Before sharing logs publicly**, please enable the **"Anonymize logs"** option in the integration settings. This will automatically replace your private keys and PIN codes with fake values (e.g., `1234AB`, `1A3B5C7E`).

To enable debug logging:

```yaml
logger:
  default: info
  logs:
    custom_components.boks: debug
```

## Detailed Documentation

For comprehensive guides, please refer to:

*   [Introduction](documentation/EN/introduction.md)
*   [Features](documentation/EN/features.md)
*   [Prerequisites](documentation/EN/prerequisites.md)
*   [Installation](documentation/EN/installation.md)
*   [Configuration](documentation/EN/configuration.md)
*   [Events & Automations (Usage)](documentation/EN/usage.md)
*   [Troubleshooting (Debugging)](documentation/EN/troubleshooting.md)

## ⚖️ Legal Notice

> **⚠️ Disclaimer:** This is an unofficial project developed for **interoperability purposes only**.
> It is not affiliated with the device manufacturer. No proprietary code or assets are distributed here.
>
> 👉 Please read the full **[Legal Disclaimer & Reverse Engineering Notice](LEGALS.md)** before using this software.