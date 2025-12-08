# Installation Guide for Boks Home Assistant Integration

This guide provides step-by-step instructions for installing the Boks Home Assistant integration. You can choose between installation via HACS (recommended) or a manual installation.

[![Open your Home Assistant instance and open a repository in the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=thib3113&repository=ha-boks&category=Integration)
[![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=boks)

## Option 1: Via HACS (Home Assistant Community Store) - Recommended

HACS simplifies the management of custom integrations, making updates easier.

1.  **Ensure HACS is installed**: If you don't have HACS installed, follow the official HACS installation guide first.
2.  **Open HACS**: In your Home Assistant frontend, navigate to **HACS**.
3.  **Go to Integrations**: Click on "Integrations" in the HACS sidebar.
4.  **Add Custom Repository**: Click the three dots in the top right corner of the screen (⋮) and select "Custom repositories".
5.  **Enter Repository Details**:
    *   **Repository URL**: `thib3113/ha-boks` (or the full GitHub URL of this repository).
    *   **Category**: Select "Integration".
6.  **Add and Download**: Click "Add". The repository should now appear. Search for "Boks" in HACS, then click on it and select "Download".
7.  **Restart Home Assistant**: After the download is complete, **restart your Home Assistant instance** for the integration to be loaded.

## Option 2: Manual Installation

If you prefer not to use HACS or encounter issues, you can install the integration manually.

1.  **Download the Release**: Go to the [releases page of this repository](https://github.com/thib3113/ha-boks/releases) and download the `boks.zip` file from the latest release.
2.  **Unzip the File**: Extract the contents of the downloaded `boks.zip` file. You should find a folder named `boks`.
3.  **Copy to Custom Components**: Copy the entire `boks` folder into your Home Assistant's `custom_components/` directory.
    *   The `custom_components` directory is typically located in your Home Assistant configuration directory (e.g., `/config/custom_components/`). If it doesn't exist, create it.
    *   The final path should look like `path/to/homeassistant/config/custom_components/boks/`.
4.  **Restart Home Assistant**: After copying the files, **restart your Home Assistant instance** for the integration to be loaded.
