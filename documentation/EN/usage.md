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

## 🚀 Blueprint (Simplified Automations)

To simplify configuration, we provide a ready-to-use **Blueprint** that bundles the most common scenarios.

### 📥 [Import Boks Notifications Blueprint](../../blueprints/automation/boks_notifications.yaml)

This Blueprint allows you to configure in a few clicks:
*   ✅ Parcel Delivered Notification
*   🚪 Door Opening Notification
*   🚨 Alert on Invalid Code
*   🔋 Low Battery Alert

To use it:
1.  Copy the `blueprints/automation/boks_notifications.yaml` file to your `blueprints/automation/` folder.
2.  Go to **Settings > Automations & Scenes > Blueprints**.
3.  Search for "Boks Notifications" and click "Create Automation".

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

### 2. Door Left Open Alert
If the door remains open for more than 5 minutes, receive an alert.
*Note: The `lock` entity is considered "unlocked" as long as the door is physically open.*

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
