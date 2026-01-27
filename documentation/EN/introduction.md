# Boks Integration for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub License](https://img.shields.io/github/license/thib3113/ha-boks?color=blue)](../../LICENSE)

Welcome to the documentation for the Boks Home Assistant integration.

## 📚 Table of Contents

This guide is divided into several sections to assist you from installation to advanced usage:

*   **[Introduction](introduction.md)**: Project overview.
*   **[Features](features.md)**: Discover what this integration can do (Control, Sensors, Parcel Tracking...).
*   **[Prerequisites](prerequisites.md)**: Hardware (Bluetooth Proxy) and Credentials (Master Code vs Keys) required.
*   **[Installation](installation.md)**: Step-by-step guide (HACS or Manual).
*   **[Configuration](configuration.md)**: How to set up the integration and enable advanced features.
*   **[Usage (Events & Automations)](usage.md)**: Examples for creating automations based on parcel deliveries.
*   **[Troubleshooting](troubleshooting.md)**: Solving common issues and enabling logs.

---

## Project Overview

This is a custom integration for **Home Assistant** that allows you to control and monitor your **Boks** connected parcel box via **Bluetooth Low Energy (BLE)**.

It allows you to open your Boks directly from Home Assistant without needing the official mobile app or an internet connection (once configured), leveraging Home Assistant's Bluetooth capabilities (local adapter or ESPHome proxies).

## Key Features

*   🔓 **Local Unlocking** via Bluetooth.
*   📦 **Smart Parcel Tracking**: Interactive To-Do list with automatic code generation (requires configuration key).
*   🔋 **Battery Monitoring**.
*   📜 **History** of openings and deliveries.

---

## ⚖️ Legal Notice

> **⚠️ Disclaimer:** This is an unofficial project developed for **interoperability purposes only**.
> It is not affiliated with the device manufacturer. No proprietary code or assets are distributed here.
>
> 👉 Please read the full **[Legal Disclaimer & Reverse Engineering Notice](../../LEGALS.md)** before using this software.
