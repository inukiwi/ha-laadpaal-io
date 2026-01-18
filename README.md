# Laadpaal.io integration for Home Assistant

## About this repo
This integration provides real-time status updates for charging stations in The Netherlands using the API at [Laadpaal.io](https://laadpaal.io) (this service is also maintained by me ([@inukiwi](https://github.com/inukiwi))). The data is sourced from [DOT-NL by NDW](https://www.ndw.nu/dataportalen/dot-nl). It was created to monitor the availability of nearby or specific charging points directly within your dashboards without needing to check external apps constantly. You can also automate notifications for when a chargepoint becomes available so you can charge your EV.

---

## Installation

I recommend installing it through [HACS](https://github.com/hacs/integration)

### Installing via HACS
1. Go to **HACS** -> **Integrations**.
1. Click the three dots in the top right corner and select **Custom repositories**.
1. Add this repository URL into your HACS custom repositories and select **Integration** as the category.
1. Search for **Laadpaal.io** and download it.
1. **Restart** your Home Assistant instance.

### Manual Installation
1. Download the source code of this repository.
2. Copy the `custom_components/laadpaal_io` folder to the `custom_components` folder in your Home Assistant configuration directory.
3. **Restart** your Home Assistant instance.

---

## Setup the Integration

1. Go to **Settings** -> **Devices & Services**.
1. Click **Add Integration**.
1. Search for **Laadpaal.io**.
1. **Location Selection**: Use the map selector to pick the approximate location of your charging station.
1. **Station Selection**: Select your specific charging station from the list of nearby locations found within a 200m radius.
1. You're all set!

---

## Functionality

### Binary Sensors
These sensors indicate whether a specific charging point or the entire station is in use.
- **Charge Point Occupied**: Indicates if a specific charge point (UID) is currently occupied (On/Bezet) or available (Off/Beschikbaar).
- **Charging Station Occupied**: A general sensor that turns 'On' if there are no available charge points left at the selected location.

### Sensors
- **Available Charge Points**: A numeric sensor that tracks the total number of free charging spots at the station.

---

## Technical Details
- **IoT Class**: Cloud Polling
- **Domain**: `laadpaal_io`
- **Platforms**: Binary Sensor, Sensor