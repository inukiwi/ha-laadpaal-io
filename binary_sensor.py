"""Binary sensors for the Laadpaal.io integration."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_FEATURE_ID, CONF_LOCATION_ID
from .coordinator import LaadpaalCoordinator


async def async_setup_entry(_hass, entry, async_add_entities):
    """Set up the charging station binary sensor."""
    coordinator = entry.runtime_data.coordinator
    unique_id_base = entry.data.get(CONF_LOCATION_ID) or entry.data[CONF_FEATURE_ID]

    async_add_entities([ChargingStationAvailableSensor(coordinator, unique_id_base)])


class ChargingStationAvailableSensor(
    CoordinatorEntity[LaadpaalCoordinator], BinarySensorEntity
):
    """Sensor to indicate if the charging station has available charge points."""

    _attr_has_entity_name = True
    _attr_translation_key = "chargingstation_available"

    def __init__(self, coordinator: LaadpaalCoordinator, unique_id_base: str) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{unique_id_base}_available"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the charging station."""
        return self.coordinator.device_info

    @property
    def is_on(self):
        """Check if there are available charge points."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.available_chargepoints > 0

    @property
    def icon(self):
        """Return the icon based on the charge point status."""
        if self.is_on:
            return "mdi:car-off"
        return "mdi:car-electric"
