"""Laadpaal.io coordinator."""

from datetime import timedelta
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = 300


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Charging station configuration setup."""
    api = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = LaadpaalCoordinator(hass, config_entry, api)

    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        LaadpaalEntity(coordinator, idx) for idx, ent in enumerate(coordinator.data)
    )


class LaadpaalCoordinator(DataUpdateCoordinator):
    """Laadpaal coordinator."""

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the charging station."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.location_id)},
            name=self.data.get("name", "Charging Station"),
        )

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, api) -> None:
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
        self.location_id = config_entry.data["location_id"]

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        return await self.api.async_get_location(self.location_id)


class LaadpaalEntity(CoordinatorEntity, BinarySensorEntity):
    """An entity using CoordinatorEntity."""

    def __init__(self, coordinator, idx) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, context=idx)
        self.idx = idx

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_is_on = self.coordinator.data[self.idx]["state"]
        self.async_write_ha_state()
