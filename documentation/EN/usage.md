# Events & Automations (Usage) in Boks Home Assistant Integration

This document explains how to use the events exposed by the Boks integration for Home Assistant automations. Leveraging these events allows you to create powerful automations based on the activity of your Boks device.

## Event Entity Overview

The Boks integration exposes an `event` entity (e.g., `event.boks_logs`) that fires whenever new log data is retrieved from your Boks device. This entity acts as a central point for all historical activities recorded by your Boks.

When an event fires, it carries an `event_type` attribute and potentially other data that describes what happened.

## Available Event Types

The following are common `event_type` values you might receive:

*   `door_opened`: The Boks door was opened.
*   `door_closed`: The Boks door was closed.
*   `code_ble_valid`: A valid code was entered via Bluetooth Low Energy (BLE).
*   `code_key_valid`: A valid code was entered via the physical keypad.
*   `code_ble_invalid`: An invalid code was attempted via BLE.
*   `code_key_invalid`: An invalid code was attempted via the physical keypad.
*   `error`: An error occurred on the Boks device.
*   ... and potentially other event types indicating various states or actions.

## Automation Trigger Examples

You can use the "Event" trigger in Home Assistant automations to react to specific `event_type` values from your Boks.

### Example 1: Notify when Boks door is opened

This automation sends a notification to your mobile app every time the Boks door is opened.

```yaml
alias: Notify when Boks door is opened
description: "Sends a notification to your phone when the Boks door is opened."
trigger:
  - platform: state
    entity_id: event.boks_logs # Monitor the Boks event entity
condition:
  - condition: template # Use a template condition to check the event_type attribute
    value_template: "{{ state_attr('event.boks_logs', 'event_type') == 'door_opened' }}"
action:
  - service: notify.mobile_app_iphone # Replace with your notification service
    data:
      message: "Your Boks has been opened!"
mode: queued
```

*   **Explanation**:
    *   The `trigger` listens for any state change on `event.boks_logs`.
    *   The `condition` then checks if the `event_type` attribute of `event.boks_logs` is `door_opened`.
    *   If the condition is met, the `action` sends a notification.

### Example 2: Log all Boks events to a persistent notification

This automation creates a persistent notification in Home Assistant for every event from your Boks.

```yaml
alias: Log all Boks events
description: "Creates a persistent notification for every event reported by the Boks."
trigger:
  - platform: state
    entity_id: event.boks_logs
action:
  - service: persistent_notification.create
    data_template:
      title: "Boks Event: {{ state_attr('event.boks_logs', 'event_type') }}"
      message: "New event received from Boks: {{ states('event.boks_logs') }} at {{ now().strftime('%H:%M:%S') }}. Details: {{ state_attr('event.boks_logs', 'event_data') | tojson }}"
mode: queued
```

*   **Explanation**:
    *   This automation triggers on any state change of `event.boks_logs`.
    *   It then creates a persistent notification with the `event_type` in the title and a more detailed message including the raw state and any `event_data`.

[Add more examples or detail on specific use cases for automations.]
