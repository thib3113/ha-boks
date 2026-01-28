# Usage: Services, Events & Automations

This document is a complete guide to interacting with your Boks via Home Assistant, whether manually via services or automatically via automations.

## 🛠️ Available Services

The Boks integration exposes several services to control your device. You can call them from **Developer Tools > Services** or use them in your scripts and automations.

### Door Control

#### `lock.open` (or `boks.open_door`)
Opens the Boks door.
*   **Entity**: `lock.your_boks_door`
*   **Code (Optional)**: If omitted, the integration uses the configured "Master Code". If you specify a code, that one will be used (useful for testing single-use codes).

### Parcel Management

#### `todo.add_item` (or `boks.add_parcel`)
Adds a parcel to be expected.
*   **Entity**: `todo.your_boks_parcels`
*   **Description**: The name of the parcel.
    *   *Auto Mode*: Just enter the name (e.g., "Amazon"). The integration generates a code and updates the title (e.g., "1234AB - Amazon").
    *   *Manual Mode*: Enter the code followed by the name (e.g., "1234AB - Amazon").

### Code Management

#### `boks.add_master_code` / `boks.delete_master_code`
Manages master codes (family access, regular delivery person).
*   **Index**: Memory slot (0-99).
*   **Code**: The 6-character PIN code.

#### `boks.add_single_code` / `boks.delete_single_code`
Manages single-use codes manually (if you don't use the Todo list).

### Maintenance

#### `boks.sync_logs`
Forces an immediate synchronization of logs with the Boks (requires active Bluetooth connection).

#### `boks.set_configuration`
Modifies internal settings (e.g., enable/disable La Poste badge recognition).

---

## 📡 Event Details

The Boks integration emits rich events on the Home Assistant bus but also stores recent history in its sensors.

### 1. Entity: Last Event (`sensor.xxx_last_event`)

The `sensor.<name>_last_event` entity is the easiest way to view the state.
*   **State**: Contains the type of the very last event (e.g., `door_opened`, `code_ble_valid`).
*   **Attribute `last_10_events`**: Contains a list of the 10 most recent events (newest to oldest), with all their details (timestamp, code used, etc.). Useful for displaying a history in a Lovelace card.

### 2. Bus Events

For reactive automations, prefer bus events.

#### `boks_log_entry`
This is the "raw" event, emitted for **each** log line retrieved from the Boks.
*   **When**: At each new action (opening, error, etc.) synchronized.
*   **Data**: Contains `type`, `timestamp`, `device_id`, `code`, `user`, etc.
*   **Usage**: Generic automations (intrusion alert, door open).

#### `boks_parcel_completed`
High-level event, specific to parcel delivery.
*   **When**: A PIN code matching a `todo` list task was used.
*   **Data**:
    *   `code`: The PIN code used.
    *   `description`: The name of the parcel (e.g., "Amazon").
*   **Usage**: Custom notification "Your Amazon parcel has arrived!".

#### `boks_logs_retrieved`
Technical end-of-sync event.
*   **When**: A Bluetooth sync session is finished and new logs have been processed.
*   **Data**: Contains a complete list of logs retrieved during this session.
*   **Usage**: Debugging or batch processing if you don't want to trigger an automation 50 times if 50 logs arrive at once.

---

## 🚀 Blueprints (Ready-to-use Automations)

To make things easier, we provide several Blueprints tailored to different needs. Click the buttons to import them directly into your Home Assistant.

### 1. Parcel Delivered Notification
Sends you a notification when a code from the parcel list is used.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fthib3113%2Fha-boks%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fboks_parcel_delivered.yaml)

### 2. Security Alert (Invalid Code)
Immediate critical notification if an incorrect PIN code is entered on the Boks.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fthib3113%2Fha-boks%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fboks_security_alert.yaml)

### 3. Low Battery Alert
Robust battery monitoring (handles HA restarts and delays to avoid false alerts).

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fthib3113%2Fha-boks%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fboks_battery_alert.yaml)

### 4. Door Left Open Alert
Smartly checks if the door has been left open.
*   *Feature*: Performs an active check (Bluetooth sync) before sending the alert to ensure the door is truly open.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fthib3113%2Fha-boks%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fboks_door_left_open.yaml)

---

## 🤖 Automation Examples (Manual Configuration)

If you prefer to create your own custom automations, here are concrete examples.

### 1. Delivery Notification (Parcel Deposited)
Uses the dedicated `boks_parcel_completed` event.

```yaml
alias: "Boks: Parcel Delivered"
description: "Sends a notification when a parcel code is used."
trigger:
  - platform: event
    event_type: boks_parcel_completed
condition: []
action:
  - service: notify.mobile_app_your_phone
    data:
      title: "📦 Parcel Delivered!"
      message: "The parcel '{{ trigger.event.data.description }}' was deposited using code {{ trigger.event.data.code }}."
```

### 2. Door Left Open Alert (Simple Version)
If the door remains open for more than 5 minutes, receive an alert.
*Note: For a more reliable version that checks the actual status, use the provided Blueprint.*

```yaml
alias: "Boks: Door Left Open"
trigger:
  - platform: state
    entity_id: lock.my_boks_door
    to: "unlocked"
    for:
      hours: 0
      minutes: 5
      seconds: 0
action:
  - service: notify.mobile_app_your_phone
    data:
      message: "⚠️ Attention, the Boks door has been open for 5 minutes!"
```

### 3. Low Battery Alert
Monitor the battery level to never be caught off guard.

```yaml
alias: "Boks: Low Battery"
trigger:
  - platform: numeric_state
    entity_id: sensor.my_boks_battery
    below: 20
action:
  - service: notify.mobile_app_your_phone
    data:
      message: "🔋 Boks battery low ({{ states('sensor.my_boks_battery') }}%). Consider replacing the batteries."
```

### 4. Intrusion Attempt (Wrong Code)
Get alerted if someone tries invalid codes.

```yaml
alias: "Boks: Invalid Code"
trigger:
  - platform: state
    entity_id: event.my_boks_logs
    attribute: event_type
    to: "code_ble_invalid"
  - platform: state
    entity_id: event.my_boks_logs
    attribute: event_type
    to: "code_key_invalid"
action:
  - service: notify.mobile_app_your_phone
    data:
      message: "🚨 Invalid code attempted on Boks!"
```

### 5. Opening Notification (Generic)
Know who opened the box (Family, Postman, etc.).

```yaml
alias: "Boks: New Opening"
trigger:
  - platform: state
    entity_id: event.my_boks_logs
    attribute: event_type
    to: 
      - "code_ble_valid"
      - "code_key_valid"
      - "nfc_opening"
      - "key_opening"
action:
  - service: notify.mobile_app_your_phone
    data:
      title: "Boks Opened"
      message: >
        The Boks was opened.
        Type: {{ state_attr('event.my_boks_logs', 'event_type') }}
        Info: {{ state_attr('event.my_boks_logs', 'extra_data') }}
```
