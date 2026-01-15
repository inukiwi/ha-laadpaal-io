"""The Laadpalen integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import LaadpaalApi

_PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)

type LaadpaalConfigEntry = ConfigEntry[LaadpaalApi]


async def async_setup_entry(hass: HomeAssistant, entry: LaadpaalConfigEntry) -> bool:
    """Set up Laadpalen from a config entry."""

    api = LaadpaalApi(hass)
    try:
        await api.async_test_connection()
    except ValueError as err:
        _LOGGER.error("Error connecting to laadpaal.io API: %s", err)
        return False
    entry.runtime_data = api

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: LaadpaalConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
