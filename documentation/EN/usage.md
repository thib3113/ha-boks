# Events & Automations (Usage) in Boks Home Assistant Integration

This document explains how to use the events exposed by the Boks integration for Home Assistant automations. Leveraging these events allows you to create powerful automations based on the activity of your Boks device.

## Event Entity Overview

The Boks integration exposes an `event` entity (e.g., `event.boks_logs`) that fires whenever new log data is retrieved from your Boks device. This entity acts as a central point for all historical activities recorded by your Boks.

In addition to the `event` entity, the integration also emits events on the Home Assistant event bus with the event type `boks_log_entry`. These events contain the same data as the `event` entity and can be used in automations as an alternative to state-based triggers.

When an event fires, it carries an `event_type` attribute and potentially other data that describes what happened.

## Available Event Types

The following are common `event_type` values you might receive:

*   `door_opened`: The Boks door was opened.
*   `door_closed`: The Boks door was closed.
*   `code_ble_valid`: A valid code was entered via Bluetooth Low Energy (BLE).
*   `code_key_valid`: A valid code was entered via the physical keypad.
*   `code_ble_invalid`: An invalid code was attempted via BLE.
*   `code_key_invalid`: An invalid code was attempted via the physical keypad.
*   `nfc_opening`: Boks opened via an NFC badge.
*   `nfc_tag_registering`: A badge was scanned during a registration procedure.
*   `error`: An error occurred on the Boks device.
*   ... and potentially other event types indicating various states or actions.
