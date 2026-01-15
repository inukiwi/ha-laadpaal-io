"""Config flow for the Laadpalen integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_LATITUDE, CONF_LOCATION, CONF_LONGITUDE
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

from .api import LaadpaalApi
from .const import CONF_LOCATION_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)


class LaadpaalConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for a chargingpoint."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.latitude: float | None = None
        self.longitude: float | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            self.latitude = user_input[CONF_LOCATION][CONF_LATITUDE]
            self.longitude = user_input[CONF_LOCATION][CONF_LONGITUDE]
            return await self.async_step_location()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_LOCATION,
                        default={
                            CONF_LATITUDE: self.hass.config.latitude,
                            CONF_LONGITUDE: self.hass.config.longitude,
                        },
                    ): selector.LocationSelector(
                        selector.LocationSelectorConfig(radius=False)
                    ),
                }
            ),
        )

    async def async_step_location(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the locations step."""
        if user_input is not None:
            location = await LaadpaalApi(self.hass).async_get_location_details(
                user_input[CONF_LOCATION_ID]
            )
            return self.async_create_entry(
                title=location["name"],
                data={
                    CONF_LOCATION_ID: user_input[CONF_LOCATION_ID],
                },
            )

        if self.latitude is None or self.longitude is None:
            _LOGGER.error("Latitude and/or longitude is not defined")
            return self.async_abort(reason="missing_coordinates")

        api = LaadpaalApi(self.hass)

        locations = await api.async_get_locations_in_radius(
            self.latitude, self.longitude, radius=200.0
        )

        location_options = [
            selector.SelectOptionDict(
                value=location["id"],
                label=location["name"] + " (" + location["address"] + ")",
            )
            for location in locations
        ]

        return self.async_show_form(
            step_id="location",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LOCATION_ID): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=location_options)
                    )
                }
            ),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
