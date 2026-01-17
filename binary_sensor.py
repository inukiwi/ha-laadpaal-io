"""Binary sensors for the Laadpaal.io integration."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import LaadpaalCoordinator


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up binary sensors for each EVSE."""
    coordinator = entry.runtime_data.coordinator
    api = entry.runtime_data.api

    location_id = entry.data["location_id"]
    location = await api.async_get_location(location_id)

    entities = [
        ChargePointOccupiedSensor(coordinator, location_id, evse["uid"])
        for evse in location.get("evses", [])
    ] + [ChargingStationOccupiedSensor(coordinator, location_id)]

    async_add_entities(entities)


class ChargePointOccupiedSensor(
    CoordinatorEntity[LaadpaalCoordinator], BinarySensorEntity
):
    """Sensor for a specific charge point of the charging station."""

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the charging station."""
        return self.coordinator.device_info

    _attr_device_class = BinarySensorDeviceClass.PLUG
    _attr_has_entity_name = True
    _attr_translation_key = "chargepoint_occupied"

    def __init__(self, coordinator, location_id, chargepoint_uid) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.chargepoint_uid = chargepoint_uid
        self._attr_unique_id = f"{location_id}_{chargepoint_uid}_occupied"
        self._attr_translation_placeholders = {"chargepoint_uid": chargepoint_uid}

    @property
    def _evse_data(self):
        """Helper to get the current EVSE data from the coordinator."""
        evses = self.coordinator.data.get("evses", [])
        return next((e for e in evses if e["uid"] == self.chargepoint_uid), None)

    @property
    def is_on(self):
        """Check the status of this specific charge point."""
        evse = self._evse_data

        if evse:
            return evse.get("status") != "AVAILABLE"
        return None

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        evse = self._evse_data
        if evse:
            return {"status": evse.get("status")}
        return {}


class ChargingStationOccupiedSensor(
    CoordinatorEntity[LaadpaalCoordinator], BinarySensorEntity
):
    """Sensor to indicate if the charging station has no available charge points."""

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the charging station."""
        return self.coordinator.device_info

    _attr_device_class = BinarySensorDeviceClass.PLUG
    _attr_has_entity_name = True
    _attr_translation_key = "chargingstation_occupied"

    def __init__(self, coordinator, location_id) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{location_id}_occupied"

    @property
    def is_on(self):
        """Check if there are no available charge points."""
        evses = self.coordinator.data.get("evses", [])
        return not any(evse.get("status") == "AVAILABLE" for evse in evses)
