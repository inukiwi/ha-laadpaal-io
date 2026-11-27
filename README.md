# Laadpaal.io integration for Home Assistant

## About this repo
### English
This integration provides real-time status updates for charging stations in The Netherlands by using data from [DOT-NL by NDW](https://www.ndw.nu/dataportalen/dot-nl). It is created to monitor the availability of nearby or specific charging stations within your dashboards without needing to check external apps constantly. With these sensors you also automate notifications for when a chargepoint becomes available so you can charge your EV.

### Dutch
Deze integratie biedt real-time statusupdates voor laadpalen in Nederland via de data van [DOT-NL van het NDW](https://www.ndw.nu/dataportalen/dot-nl). Het is gemaakt om de beschikbaarheid van nabijgelegen of specifieke laadstations direct in je dashboards te monitoren, zonder constant externe apps te hoeven checken. Met deze sensoren kan je ook meldingen automatiseren voor wanneer een laadpunt beschikbaar komt, zodat je je EV kunt opladen.

> Version 2.0.0 and onwards directly fetch the data from DOT-NL. Versions below 2.0.0 still use the old Laadpaal.io APIs
>
> Vanaf versie 2.0.0 gebruikt deze integratie direct DOT-NL data. Versies lager dan 2.0.0 maken nog gebruik van de Laadpaal.io API's.

## Notes about data freshness
### English
The data is retrieved from DOT-NL every 5 minutes by default, but this data can be outdated depending on the charging station. The NDW depends on charging providers to supply the information and not every provider has a direct connection as of this moment, causing some charging stations to only be refreshed every 6 hours.

### Dutch
De data wordt standaard elke 5 minuten opgehaald vanuit DOT-NL, maar deze data kan afhankelijk van de laadpaal enigzins verouderd zijn. Het NDW is afhankelijk van de laadpaalaanbieders en nog niet elke aanbieder heeft een directe koppeling, waardoor sommige laadpalen alleen elke 6 uur worden bijgewerkt.

---

## Installation

I recommend installing it through the Home Assistant Marketplace.

### Installing via Marketplace
[![Open your Home Assistant instance and open a repository in the Marketplace.](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=inukiwi&repository=ha-laadpaal-io)

Use this button or follow the steps below.
1. Go to **Settings** -> **Marketplace**.
1. Click on **Add from link** in the top right corner and paste the link of this repository (https://github.com/inukiwi/ha-laadpaal-io).
1. Search for **Laadpaal.io** and download it.

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
- **Charging station available**: A general sensor that turns 'On' if there are any available charge points at the selected location.

### Sensors
- **Available charge points**: A numeric sensor that tracks the total number of free charging spots at the station.

---

## Technical Details
- **IoT Class**: Cloud Polling
- **Domain**: `laadpaal_io`
- **Platforms**: Binary Sensor, Sensor