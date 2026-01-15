"""API client for laadpaal.io integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)


class LaadpaalApi:
    """Client for laadpaal.io API."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the API client."""
        self.hass = hass
        self._session = async_get_clientsession(hass)
        self._base_url = "https://laadpaal.io/api/v1"

    async def async_test_connection(self) -> None:
        """Test API connection and authentication."""
        url = f"{self._base_url}/status"
        try:
            async with self._session.get(
                url, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    raise ValueError(f"API returned status {resp.status}")
                data = await resp.json()
                if not data.get("status", "ok"):
                    raise ValueError("API status not ok")
        except TimeoutError as err:
            raise ConnectionError("Timeout connecting to laadpaal.io API") from err
        except aiohttp.ClientError as err:
            raise ConnectionError("Error communicating with laadpaal.io API") from err

    async def async_get_locations_in_radius(
        self, latitude: float, longitude: float, radius: float
    ) -> list[dict[str, Any]]:
        """Get charging locations within a certain radius."""
        params = {"lat": latitude, "lon": longitude, "radius": radius}
        return await self.async_get_data("locations", params=params)

    async def async_get_location_details(self, location_id: str) -> dict[str, Any]:
        """Get details for a specific charging location."""
        return await self.async_get_data(f"locations/{location_id}")

    async def async_get_data(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> Any:
        """Fetch data from a given API endpoint."""
        url = f"{self._base_url}/{endpoint}"
        try:
            async with self._session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                resp.raise_for_status()
                return await resp.json()
        except TimeoutError as err:
            raise ConnectionError("Timeout fetching data from laadpaal.io API") from err
        except aiohttp.ClientError as err:
            raise ConnectionError("Error fetching data from laadpaal.io API") from err
