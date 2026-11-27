"""Laadpaal.io coordinator."""

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DotNlFeature
from .const import (
    CONF_ADDRESS,
    CONF_CPO_ID,
    CONF_FEATURE_ID,
    CONF_MANUFACTURER,
    DOMAIN,
    POLL_RADIUS_METERS,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = 300


class LaadpaalCoordinator(DataUpdateCoordinator[DotNlFeature]):
    """Laadpaal coordinator."""

    def __init__(
        self, hass: HomeAssistant, config_entry: ConfigEntry, api, legacy_api
    ) -> None:
        """Initialize laadpaal coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Laadpaal sensor",
            config_entry=config_entry,
            update_interval=timedelta(seconds=SCAN_INTERVAL),
            always_update=False,
        )
        self.api = api
        self.legacy_api = legacy_api
        self.feature_id = config_entry.data[CONF_FEATURE_ID]
        self.latitude = float(config_entry.data[CONF_LATITUDE])
        self.longitude = float(config_entry.data[CONF_LONGITUDE])
        self.address = config_entry.data.get(CONF_ADDRESS, config_entry.title)
        self.cpo_id = config_entry.data.get(CONF_CPO_ID)
        self.manufacturer = config_entry.data.get(CONF_MANUFACTURER)

    @property
    def device_info(self):
        """Return device information for the charging station."""
        name = self.data.address if self.data is not None else self.address
        manufacturer = (
            self.data.manufacturer if self.data is not None else self.manufacturer
        )
        return DeviceInfo(
            identifiers={(DOMAIN, self.feature_id)},
            name=name,
            manufacturer=manufacturer or None,
        )

    async def _async_update_data(self):
        """Fetch charging station data from DOT-NL within a 10 meter bbox."""
        try:
            feature = await self.api.async_get_feature_by_id(
                self.latitude,
                self.longitude,
                self.feature_id,
                radius=POLL_RADIUS_METERS,
            )
        except ConnectionError as err:
            raise UpdateFailed(f"Error communicating with DOT-NL API: {err}") from err

        if feature is None:
            raise UpdateFailed(
                f"Charging station {self.feature_id} was not found in DOT-NL response"
            )

        return feature
