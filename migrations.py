"""Config entry migration helpers for Laadpaal.io."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)

from .api import DotNlApi, LaadpaalApi, extract_coordinates
from .const import (
    CONF_ADDRESS,
    CONF_CPO_ID,
    CONF_FEATURE_ID,
    CONF_LOCATION_ID,
    CONF_MANUFACTURER,
    DOMAIN,
    MIGRATION_ISSUE_PREFIX,
    MIGRATION_RADIUS_METERS,
)

_LOGGER = logging.getLogger(__name__)


def migration_issue_id(entry_id: str) -> str:
    """Build the repair issue ID for a config entry needing reconfiguration."""
    return f"{MIGRATION_ISSUE_PREFIX}_{entry_id}"


def async_create_migration_issue(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Create a repair issue instructing the user to reconfigure the entry."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        migration_issue_id(entry.entry_id),
        is_fixable=False,
        is_persistent=True,
        severity=ir.IssueSeverity.ERROR,
        translation_key="migration_reconfigure_required",
        translation_placeholders={"entry_title": entry.title},
    )


def has_dotnl_config(data: Mapping[str, Any]) -> bool:
    """Return whether config entry data contains valid DOT-NL station fields."""
    feature_id = data.get(CONF_FEATURE_ID)
    latitude = data.get(CONF_LATITUDE)
    longitude = data.get(CONF_LONGITUDE)
    return (
        isinstance(feature_id, str)
        and bool(feature_id.strip())
        and isinstance(latitude, (int, float))
        and not isinstance(latitude, bool)
        and isinstance(longitude, (int, float))
        and not isinstance(longitude, bool)
    )


def remove_stale_evse_entities(
    hass: HomeAssistant, entry_id: str, old_location_id: str
) -> None:
    """Remove legacy per-EVSE binary sensor entities for this entry."""
    entity_registry = er.async_get(hass)
    station_unique_id = f"{old_location_id}_available"
    evse_prefix = f"{old_location_id}_"

    for entity_entry in list(
        er.async_entries_for_config_entry(entity_registry, entry_id)
    ):
        if (
            entity_entry.platform != DOMAIN
            or entity_entry.domain != Platform.BINARY_SENSOR
        ):
            continue
        if (
            entity_entry.unique_id.startswith(evse_prefix)
            and entity_entry.unique_id.endswith("_available")
            and entity_entry.unique_id != station_unique_id
        ):
            entity_registry.async_remove(entity_entry.entity_id)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate a legacy version 1 entry to version 2 (DOT-NL)."""
    if entry.version >= 2:
        return True

    old_location_id = entry.data.get(CONF_LOCATION_ID)
    if not isinstance(old_location_id, str) or not old_location_id.strip():
        _LOGGER.warning(
            "Cannot migrate config entry %s without a valid legacy location_id",
            entry.entry_id,
        )
        async_create_migration_issue(hass, entry)
        return True

    api = DotNlApi(hass)
    legacy_api = LaadpaalApi(hass)

    try:
        candidates = await legacy_api.async_get_multiple_locations(old_location_id)
    except (ConnectionError, ValueError, TypeError) as err:
        _LOGGER.warning(
            "Automatic migration failed while fetching candidate locations for %s: %s",
            old_location_id,
            err,
        )
        async_create_migration_issue(hass, entry)
        return True

    matching_candidate = None
    if len(candidates) == 1:
        matching_candidate = candidates[0]
    if matching_candidate is None:
        matching_candidates = [
            candidate
            for candidate in candidates
            if candidate.get("name") == entry.title
        ]
        if len(matching_candidates) != 1:
            _LOGGER.warning(
                "Automatic migration expected 1 address match for %s, found %d",
                old_location_id,
                len(matching_candidates),
            )
            async_create_migration_issue(hass, entry)
            return True
        matching_candidate = matching_candidates[0]

    candidate_address = matching_candidate.get("address")
    candidate_coords = extract_coordinates(matching_candidate)
    if candidate_coords is None:
        _LOGGER.warning(
            "Automatic migration candidate for %s has invalid coordinates",
            old_location_id,
        )
        async_create_migration_issue(hass, entry)
        return True

    cand_lat, cand_lon = candidate_coords
    try:
        features = await api.async_get_locations_in_radius(
            cand_lat, cand_lon, radius=MIGRATION_RADIUS_METERS
        )
        dotnl_feature = None
        if len(features) == 1:
            dotnl_feature = features[0]
        elif len(features) > 1:
            for feature in features:
                if feature.address == candidate_address:
                    dotnl_feature = feature
                    break
    except (ConnectionError, ValueError, TypeError) as err:
        _LOGGER.warning(
            "Automatic migration failed while querying DOT-NL for %s: %s",
            old_location_id,
            err,
        )
        async_create_migration_issue(hass, entry)
        return True

    if dotnl_feature is None:
        _LOGGER.warning(
            "Automatic migration did not find a unique DOT-NL feature for %s",
            old_location_id,
        )
        async_create_migration_issue(hass, entry)
        return True

    migrated_data: dict[str, Any] = {
        CONF_LOCATION_ID: old_location_id,
        CONF_FEATURE_ID: dotnl_feature.feature_id,
        CONF_LATITUDE: dotnl_feature.latitude,
        CONF_LONGITUDE: dotnl_feature.longitude,
        CONF_ADDRESS: dotnl_feature.address,
        CONF_CPO_ID: dotnl_feature.cpo_id,
        CONF_MANUFACTURER: dotnl_feature.manufacturer,
    }
    hass.config_entries.async_update_entry(
        entry,
        data=migrated_data,
        unique_id=dotnl_feature.feature_id,
        version=2,
    )

    device_registry = dr.async_get(hass)
    existing_device = device_registry.async_get_device(
        identifiers={(DOMAIN, old_location_id)}
    )

    if existing_device is not None and entry.entry_id in existing_device.config_entries:
        new_identifiers = (
            existing_device.identifiers - {(DOMAIN, old_location_id)}
        ) | {(DOMAIN, dotnl_feature.feature_id)}
        device_registry.async_update_device(
            existing_device.id,
            new_identifiers=new_identifiers,
            name=dotnl_feature.address,
            manufacturer=dotnl_feature.manufacturer,
        )

    remove_stale_evse_entities(hass, entry.entry_id, old_location_id)
    ir.async_delete_issue(hass, DOMAIN, migration_issue_id(entry.entry_id))

    _LOGGER.debug(
        "Migrated entry %s from legacy location %s to DOT-NL feature %s",
        entry.entry_id,
        old_location_id,
        dotnl_feature.feature_id,
    )
    return True
