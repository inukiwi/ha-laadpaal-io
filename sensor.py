"""Sensors for the Laadpaal.io integration."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_FEATURE_ID, CONF_LOCATION_ID
from .coordinator import LaadpaalCoordinator


async def async_setup_entry(_hass, entry, async_add_entities):
    """Set up sensors."""
    coordinator = entry.runtime_data.coordinator
    unique_id_base = entry.data.get(CONF_LOCATION_ID) or entry.data[CONF_FEATURE_ID]

    async_add_entities([AvailableChargePointsSensor(coordinator, unique_id_base)])


class AvailableChargePointsSensor(CoordinatorEntity[LaadpaalCoordinator], SensorEntity):
    """Sensor reporting the number of available charge points at the station."""

    _attr_has_entity_name = True
    _attr_translation_key = "available_chargepoints"
    _attr_icon = "mdi:ev-station"

    def __init__(self, coordinator, unique_id_base):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{unique_id_base}_available_chargepoints"

    @property
    def device_info(self):
        """Return device information for the charging station."""
        return self.coordinator.device_info

    @property
    def native_value(self):
        """Check the number of available charge points."""
        if self.coordinator.data is None:
            return 0
        return self.coordinator.data.available_chargepoints

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if self.coordinator.data is None:
            return {}
        return {"total_chargepoints": self.coordinator.data.total_chargepoints}
