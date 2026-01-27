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

The Boks integration emits rich events that you can use for advanced automations.

### Entity and Event Bus

You can listen to events in two ways:
1.  **Entity**: `event.your_boks_logs` (The latest event is stored in the `event_type` attribute).
2.  **Event Bus**: `boks_log_entry` (Contains the full payload for each new event).

### Data Structure

Here is the data available in the event payload (`trigger.event.data`):

| Field | Description | Example |
| :--- | :--- | :--- |
| `type` | The event type (see list below) | `code_ble_valid` |
| `device_id` | The Home Assistant device ID | `abcdef123456...` |
| `timestamp` | Date and time of the event | `2023-10-27T10:00:00+00:00` |
| `code` | The PIN code used (if applicable) | `1234AB` |
| `user` | User index or name (if known) | `0` (Master Code Index) |
| `extra_data` | Additional raw data | `{...}` |

### Event Types (`event_type`)

| Type | Description |
| :--- | :--- |
| `door_opened` | The door was opened. |
| `door_closed` | The door was closed. |
| `code_ble_valid` | Successful opening via Bluetooth (App or HA). |
| `code_key_valid` | Successful opening via the physical keypad. |
| `code_ble_invalid` | Incorrect code entered via Bluetooth. |
| `code_key_invalid` | Incorrect code entered on the keypad. |
| `nfc_opening` | Opening via an NFC badge. |
| `key_opening` | Opening via the mechanical backup key. |
| `error` | Generic system error. |
| `power_on` | The device powered on. |
| `power_off` | The device powered off (e.g., batteries removed). |
| `ble_reboot` | The Bluetooth module rebooted. |
| `history_erase` | The log history was erased. |

---

## 🚀 Blueprints (Ready-to-use Automations)

To make things easier, we provide several Blueprints tailored to different needs.

### 📥 1. [Parcel Delivered Notification](../../blueprints/automation/boks_parcel_delivered.yaml)
Sends you a notification when a code from the parcel list is used.

### 📥 2. [Security Alert (Invalid Code)](../../blueprints/automation/boks_security_alert.yaml)
Immediate critical notification if an incorrect PIN code is entered on the Boks.

### 📥 3. [Low Battery Alert](../../blueprints/automation/boks_battery_alert.yaml)
Robust battery monitoring (handles HA restarts and delays to avoid false alerts).

### 📥 4. [Door Left Open Alert](../../blueprints/automation/boks_door_left_open.yaml)
Smartly checks if the door has been left open.
*   *Feature*: Performs an active check (Bluetooth sync) before sending the alert to ensure the door is truly open.

---

## 🤖 Automation Examples (Manual Configuration)

If you prefer to create your own custom automations, here are concrete examples.

### 1. Delivery Notification (Parcel Deposited)
Get notified when a delivery person uses the code associated with an expected parcel.

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
