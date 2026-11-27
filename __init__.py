"""The Laadpaal.io integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError

from .api import DotNlApi, LaadpaalApi
from .const import DOMAIN
from .coordinator import LaadpaalCoordinator
from .migrations import (
    async_create_migration_issue,
    async_migrate_entry as migrate_v1_to_v2,
    has_dotnl_config,
)

_PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


@dataclass
class LaadpaalData:
    """Data stored in runtime_data."""

    api: DotNlApi
    legacy_api: LaadpaalApi
    coordinator: LaadpaalCoordinator


type LaadpaalConfigEntry = ConfigEntry[LaadpaalData]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config entries to the current version."""
    if entry.version >= 2:
        return True

    return await migrate_v1_to_v2(hass, entry)


async def async_setup_entry(hass: HomeAssistant, entry: LaadpaalConfigEntry) -> bool:
    """Set up Laadpaal.io from a config entry."""
    if entry.version < 2 or not has_dotnl_config(entry.data):
        async_create_migration_issue(hass, entry)
        raise ConfigEntryError(
            translation_domain=DOMAIN,
            translation_key="migration_reconfigure_required",
            translation_placeholders={"entry_title": entry.title},
        )

    api = DotNlApi(hass)
    legacy_api = LaadpaalApi(hass)
    coordinator = LaadpaalCoordinator(hass, entry, api, legacy_api)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = LaadpaalData(
        api=api, legacy_api=legacy_api, coordinator=coordinator
    )

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: LaadpaalConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
