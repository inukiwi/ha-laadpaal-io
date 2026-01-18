"""Sensors for the Laadpaal.io integration."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import LaadpaalCoordinator


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up sensors."""
    coordinator = entry.runtime_data.coordinator

    location_id = entry.data["location_id"]

    entities = [AvailableChargePointsSensor(coordinator, location_id)]

    async_add_entities(entities)


class AvailableChargePointsSensor(CoordinatorEntity[LaadpaalCoordinator], SensorEntity):
    """Sensor for a specific charge point of the charging station."""

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the charging station."""
        return self.coordinator.device_info

    _attr_has_entity_name = True
    _attr_translation_key = "available_chargepoints"

    def __init__(self, coordinator, location_id) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{location_id}_available_chargepoints"
        self._attr_icon = "mdi:ev-station"

    @property
    def native_value(self):
        """Check the number of available charge points."""
        evses = self.coordinator.data.get("evses", [])
        return sum(1 for evse in evses if evse.get("status") == "AVAILABLE")

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        evses = self.coordinator.data.get("evses", [])
        if evses:
            return {"total_chargepoints": len(evses)}
        return {}
