"""API client for the Laadpaal.io integration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import logging
import math
from typing import Any, TypedDict, cast
from warnings import deprecated

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import POLL_RADIUS_METERS

_LOGGER = logging.getLogger(__name__)


class DotNlAvailabilityDict(TypedDict, total=False):
    """Availability object inside a DOT-NL GeoJSON feature."""

    total: int
    available: int
    power_max: int | float
    power_type: str
    connector_type: str
    connector_format: str


class DotNlGeometryDict(TypedDict):
    """Geometry object inside a DOT-NL GeoJSON feature."""

    type: str
    coordinates: list[float]


class DotNlPropertiesDict(TypedDict, total=False):
    """Properties object inside a DOT-NL GeoJSON feature."""

    address: str
    cpo_id: str
    availabilities: list[DotNlAvailabilityDict]


class DotNlFeatureDict(TypedDict, total=False):
    """GeoJSON Feature returned by DOT-NL."""

    type: str
    id: str
    geometry: DotNlGeometryDict
    properties: DotNlPropertiesDict


class DotNlFeatureCollectionDict(TypedDict, total=False):
    """GeoJSON FeatureCollection returned by DOT-NL."""

    type: str
    features: list[DotNlFeatureDict]


@dataclass(frozen=True, slots=True)
class DotNlAvailability:
    """Validated availability counts for a connector group."""

    available: int
    total: int


@dataclass(frozen=True, slots=True)
class DotNlFeature:
    """Validated DOT-NL charging station feature."""

    feature_id: str
    latitude: float
    longitude: float
    address: str
    cpo_id: str
    manufacturer: str
    availabilities: tuple[DotNlAvailability, ...]

    @property
    def available_chargepoints(self) -> int:
        """Return total available charge points across all connector groups."""
        return sum(item.available for item in self.availabilities)

    @property
    def total_chargepoints(self) -> int:
        """Return total charge points across all connector groups."""
        return sum(item.total for item in self.availabilities)


def normalize_address(address: str) -> str:
    """Normalize an address for exact case-insensitive comparison."""
    return " ".join(address.replace("\r", " ").replace("\n", " ").split()).casefold()


def _parse_float(value: Any) -> float | None:
    """Convert value to a finite float coordinate."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return numeric


def _coordinate_pair(latitude: Any, longitude: Any) -> tuple[float, float] | None:
    """Convert two values to a validated latitude/longitude pair."""
    lat = _parse_float(latitude)
    lon = _parse_float(longitude)
    if lat is None or lon is None:
        return None
    return lat, lon


def extract_coordinates(payload: Mapping[str, Any]) -> tuple[float, float] | None:
    """Extract validated (latitude, longitude) from a legacy or GeoJSON payload."""
    if not isinstance(payload, Mapping):
        return None

    for lat_key, lon_key in (
        ("latitude", "longitude"),
        ("lat", "lon"),
        ("lat", "lng"),
    ):
        if lat_key in payload and lon_key in payload:
            return _coordinate_pair(payload.get(lat_key), payload.get(lon_key))

    coords = payload.get("coordinates")
    if isinstance(coords, Mapping):
        for lat_key, lon_key in (
            ("latitude", "longitude"),
            ("lat", "lon"),
            ("lat", "lng"),
        ):
            if lat_key in coords and lon_key in coords:
                return _coordinate_pair(coords.get(lat_key), coords.get(lon_key))

    geometry = payload.get("geometry")
    if isinstance(geometry, Mapping):
        geom_coords = geometry.get("coordinates")
        if isinstance(geom_coords, (list, tuple)) and len(geom_coords) >= 2:
            return _coordinate_pair(geom_coords[1], geom_coords[0])

    return None


def parse_dotnl_feature(raw_feature: Any) -> DotNlFeature | None:
    """Parse and validate a single DOT-NL GeoJSON feature."""
    if not isinstance(raw_feature, Mapping):
        return None

    raw_id = raw_feature.get("id")
    if not isinstance(raw_id, str) or not (feature_id := raw_id.strip()):
        return None

    geometry = raw_feature.get("geometry")
    if not isinstance(geometry, Mapping):
        return None

    raw_coords = geometry.get("coordinates")
    if not isinstance(raw_coords, (list, tuple)) or len(raw_coords) < 2:
        return None

    coords = _coordinate_pair(raw_coords[1], raw_coords[0])
    if coords is None:
        return None
    latitude, longitude = coords

    properties = raw_feature.get("properties")
    if not isinstance(properties, Mapping):
        return None

    address = properties.get("address")
    if not isinstance(address, str) or not address.strip():
        return None

    raw_cpo_id = properties.get("cpo_id")
    if not isinstance(raw_cpo_id, str) or not (cpo_id := raw_cpo_id.strip()):
        return None

    manufacturer = properties.get("suboperator_name")
    if not isinstance(manufacturer, str) or not manufacturer.strip():
        manufacturer = properties.get("operator_name")
    if not isinstance(manufacturer, str) or not manufacturer.strip():
        manufacturer = properties.get("owner_name")
    if not isinstance(manufacturer, str) or not manufacturer.strip():
        manufacturer = ""

    raw_availabilities = properties.get("availabilities")
    parsed_availabilities: list[DotNlAvailability] = []
    if raw_availabilities is not None:
        if not isinstance(raw_availabilities, list):
            return None
        for raw_availability in raw_availabilities:
            if not isinstance(raw_availability, Mapping):
                return None
            available = raw_availability.get("available")
            total = raw_availability.get("total")
            if not isinstance(available, int) or not isinstance(total, int):
                return None
            parsed_availabilities.append(
                DotNlAvailability(available=available, total=total)
            )

    return DotNlFeature(
        feature_id=feature_id,
        latitude=latitude,
        longitude=longitude,
        address=address,
        cpo_id=cpo_id,
        manufacturer=manufacturer,
        availabilities=tuple(parsed_availabilities),
    )


def build_bbox(latitude: float, longitude: float, radius: float) -> str:
    """Convert a coordinate and radius in meters to a DOT-NL bbox string."""
    radius_km = radius / 1000.0
    lat_delta = radius_km / 111.32

    lat_radians = math.radians(latitude)
    lon_km_per_degree = 111.32 * max(math.cos(lat_radians), 0.000001)
    lon_delta = radius_km / lon_km_per_degree

    min_lat = max(-90.0, latitude - lat_delta)
    max_lat = min(90.0, latitude + lat_delta)
    min_lon = max(-180.0, longitude - lon_delta)
    max_lon = min(180.0, longitude + lon_delta)

    return f"{min_lon:.7f},{min_lat:.7f},{max_lon:.7f},{max_lat:.7f}"


class DotNlApi:
    """Client for DOT-NL GeoJSON API."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the API client."""
        self.hass = hass
        self._session = async_get_clientsession(hass)
        self._base_url = (
            "https://dotnl.ndw.nu/api/rest/geojson/"
            "dynamic-road-status/charge-point-data/v1"
        )

    async def _async_get_raw_dotnl_features(
        self, latitude: float, longitude: float, radius: float
    ) -> list[Any]:
        """Fetch raw GeoJSON features from DOT-NL within a bounding box."""
        bbox = build_bbox(latitude, longitude, radius)

        try:
            async with self._session.get(
                f"{self._base_url}/features",
                params={"bbox": bbox},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except TimeoutError as err:
            raise ConnectionError(
                "Timeout fetching data from DOT-NL GeoJSON API"
            ) from err
        except aiohttp.ClientError as err:
            raise ConnectionError(
                "Error fetching data from DOT-NL GeoJSON API"
            ) from err

        if not isinstance(data, Mapping):
            return []

        raw_features = data.get("features")
        if not isinstance(raw_features, list):
            return []

        return raw_features

    async def async_get_locations_in_radius(
        self, latitude: float, longitude: float, radius: float
    ) -> list[DotNlFeature]:
        """Get validated DOT-NL charging stations within a radius in meters."""
        raw_features = await self._async_get_raw_dotnl_features(
            latitude, longitude, radius
        )
        return [
            parsed
            for raw_feature in raw_features
            if (parsed := parse_dotnl_feature(raw_feature)) is not None
        ]

    async def async_get_feature_by_id(
        self,
        latitude: float,
        longitude: float,
        feature_id: str,
        radius: float = POLL_RADIUS_METERS,
    ) -> DotNlFeature | None:
        """Fetch a single DOT-NL feature by ID within a polling bounding box."""
        features = await self.async_get_locations_in_radius(
            latitude, longitude, radius=radius
        )
        matches = [f for f in features if f.feature_id == feature_id]
        if len(matches) == 1:
            return matches[0]
        return None


@deprecated("Legacy laadpaal.io API - will be removed in a future version")
class LaadpaalApi:
    """Client for legacy laadpaal.io API endpoints."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the API client."""
        self.hass = hass
        self._session = async_get_clientsession(hass)
        self._base_url = "https://laadpaal.io/api/v1"

    @deprecated("Legacy laadpaal.io endpoint - will be removed in a future version")
    async def async_get_location(self, location_id: str) -> dict[str, Any]:
        """Get details for a specific charging location."""
        return await self.async_get_data(f"locations/{location_id}")

    @deprecated("Legacy laadpaal.io endpoint - will be removed in a future version")
    async def async_get_multiple_locations(
        self, location_id: str
    ) -> list[dict[str, Any]]:
        """Get candidate charging locations for a location ID."""
        data = await self.async_get_data(f"locations/{location_id}/multiple")
        if isinstance(data, list):
            return [
                cast(dict[str, Any], dict(item))
                for item in data
                if isinstance(item, Mapping)
            ]
        if isinstance(data, Mapping):
            locations = data.get("locations")
            if isinstance(locations, list):
                return [
                    cast(dict[str, Any], dict(item))
                    for item in locations
                    if isinstance(item, Mapping)
                ]
        return []

    @deprecated("Legacy laadpaal.io endpoint - will be removed in a future version")
    async def async_get_data(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> Any:
        """Fetch data from a laadpaal.io API endpoint."""
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
