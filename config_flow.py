"""Config flow for the Laadpaal.io integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    ConfigFlow,
    ConfigFlowResult,
)
from homeassistant.const import CONF_LATITUDE, CONF_LOCATION, CONF_LONGITUDE
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir, selector

from .api import DotNlApi, DotNlFeature
from .const import (
    CONF_ADDRESS,
    CONF_CPO_ID,
    CONF_FEATURE_ID,
    CONF_LOCATION_ID,
    DOMAIN,
    SEARCH_RADIUS_METERS,
)
from .migrations import migration_issue_id, remove_stale_evse_entities

_LOGGER = logging.getLogger(__name__)


class LaadpaalConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for a Laadpaal.io charging station."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.latitude: float | None = None
        self.longitude: float | None = None
        self._features: dict[str, DotNlFeature] = {}

    def is_matching(self, other_flow: ConfigFlow) -> bool:
        """Return True if another in-progress flow matches this one."""
        if not isinstance(other_flow, LaadpaalConfigFlow):
            return False

        return (
            self.latitude is not None
            and self.longitude is not None
            and other_flow.latitude is not None
            and other_flow.longitude is not None
            and self.latitude == other_flow.latitude
            and self.longitude == other_flow.longitude
        )

    def _async_show_coordinates_form(
        self,
        *,
        step_id: str,
        errors: dict[str, str] | None = None,
    ) -> ConfigFlowResult:
        """Show the map coordinate picker form."""
        default_lat = (
            self.latitude if self.latitude is not None else self.hass.config.latitude
        )
        default_lon = (
            self.longitude if self.longitude is not None else self.hass.config.longitude
        )
        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_LOCATION,
                        default={
                            CONF_LATITUDE: default_lat,
                            CONF_LONGITUDE: default_lon,
                        },
                    ): selector.LocationSelector(
                        selector.LocationSelectorConfig(radius=False)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            self.latitude = user_input[CONF_LOCATION][CONF_LATITUDE]
            self.longitude = user_input[CONF_LOCATION][CONF_LONGITUDE]
            self._features = {}
            return await self.async_step_location()

        return self._async_show_coordinates_form(step_id="user")

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of an existing config entry."""
        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            self.latitude = user_input[CONF_LOCATION][CONF_LATITUDE]
            self.longitude = user_input[CONF_LOCATION][CONF_LONGITUDE]
            self._features = {}
            return await self.async_step_location()

        raw_lat = reconfigure_entry.data.get(CONF_LATITUDE)
        if (
            self.latitude is None
            and isinstance(raw_lat, (int, float))
            and not isinstance(raw_lat, bool)
        ):
            self.latitude = float(raw_lat)

        raw_lon = reconfigure_entry.data.get(CONF_LONGITUDE)
        if (
            self.longitude is None
            and isinstance(raw_lon, (int, float))
            and not isinstance(raw_lon, bool)
        ):
            self.longitude = float(raw_lon)

        return self._async_show_coordinates_form(step_id="reconfigure")

    async def async_step_location(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle selection of a DOT-NL charging station."""
        errors: dict[str, str] = {}
        coordinate_step_id = (
            "reconfigure" if self.source == SOURCE_RECONFIGURE else "user"
        )

        if user_input is not None:
            selected_id = user_input[CONF_FEATURE_ID]
            feature = self._features.get(selected_id)
            if feature is None:
                errors["base"] = "station_not_found"
            else:
                entry_data: dict[str, Any] = {
                    CONF_FEATURE_ID: feature.feature_id,
                    CONF_LATITUDE: feature.latitude,
                    CONF_LONGITUDE: feature.longitude,
                    CONF_ADDRESS: feature.address,
                    CONF_CPO_ID: feature.cpo_id,
                }

                if self.source == SOURCE_RECONFIGURE:
                    reconfigure_entry = self._get_reconfigure_entry()
                    existing_entry = (
                        self.hass.config_entries.async_entry_for_domain_unique_id(
                            DOMAIN, feature.feature_id
                        )
                    )
                    if (
                        existing_entry is not None
                        and existing_entry.entry_id != reconfigure_entry.entry_id
                    ):
                        return self.async_abort(reason="already_configured")

                    if old_location_id := reconfigure_entry.data.get(CONF_LOCATION_ID):
                        if isinstance(old_location_id, str) and old_location_id.strip():
                            remove_stale_evse_entities(
                                self.hass,
                                reconfigure_entry.entry_id,
                                old_location_id,
                            )

                    if reconfigure_entry.version != self.VERSION:
                        self.hass.config_entries.async_update_entry(
                            reconfigure_entry,
                            version=self.VERSION,
                        )

                    ir.async_delete_issue(
                        self.hass,
                        DOMAIN,
                        migration_issue_id(reconfigure_entry.entry_id),
                    )

                    return self.async_update_reload_and_abort(
                        reconfigure_entry,
                        unique_id=feature.feature_id,
                        title=feature.address,
                        data=entry_data,
                    )

                await self.async_set_unique_id(feature.feature_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=feature.address,
                    data=entry_data,
                )

        if self.latitude is None or self.longitude is None:
            _LOGGER.error("Latitude and/or longitude is not defined")
            return self.async_abort(reason="missing_coordinates")

        if not self._features:
            api = DotNlApi(self.hass)
            try:
                features = await api.async_get_locations_in_radius(
                    self.latitude,
                    self.longitude,
                    radius=SEARCH_RADIUS_METERS,
                )
            except ConnectionError:
                return self._async_show_coordinates_form(
                    step_id=coordinate_step_id,
                    errors={"base": "cannot_connect"},
                )
            except Exception:
                _LOGGER.exception("Unexpected error fetching DOT-NL charging stations")
                return self._async_show_coordinates_form(
                    step_id=coordinate_step_id,
                    errors={"base": "unknown"},
                )

            if not features:
                return self._async_show_coordinates_form(
                    step_id=coordinate_step_id,
                    errors={"base": "no_stations_found"},
                )

            self._features = {feature.feature_id: feature for feature in features}

        location_options = [
            selector.SelectOptionDict(
                value=feature.feature_id,
                label=feature.address,
            )
            for feature in self._features.values()
        ]

        return self.async_show_form(
            step_id="location",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_FEATURE_ID): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=location_options)
                    )
                }
            ),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
