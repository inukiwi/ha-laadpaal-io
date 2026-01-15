"""The Laadpalen integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import LaadpaalApi
from .coordinator import LaadpaalCoordinator

_PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR]

_LOGGER = logging.getLogger(__name__)


@dataclass
class LaadpaalData:
    """Data stored in runtime_data."""

    api: LaadpaalApi
    coordinator: LaadpaalCoordinator


type LaadpaalConfigEntry = ConfigEntry[LaadpaalData]


async def async_setup_entry(hass: HomeAssistant, entry: LaadpaalConfigEntry) -> bool:
    """Set up Laadpalen from a config entry."""

    api = LaadpaalApi(hass)
    try:
        await api.async_test_connection()
    except ValueError as err:
        _LOGGER.error("Error connecting to laadpaal.io API: %s", err)
        return False

    coordinator = LaadpaalCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = LaadpaalData(api=api, coordinator=coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: LaadpaalConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
