"""Example integration using DataUpdateCoordinator."""

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.sensor import (
    SensorEntity,
)
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..coordinator import KomodoCoordinator

_LOGGER = logging.getLogger(__name__)

class KomodoSensor(CoordinatorEntity[KomodoCoordinator], SensorEntity):
    """Basic sensor with common functionality."""

    def __init__(
        self,
        coordinator,
        extractor,
        category: str,
        key: str,
        id: str | None,
    ) -> None:
        """Initialize the sensor with the common coordinator."""
        super().__init__(coordinator)
        self._extractor = extractor
        self._attr_translation_key = f"${category}_${key}"
        self._attr_has_entity_name = True
        id_part = "" if id is None else f"_${id}"
        self._attr_unique_id = f"${category}${id_part}_${key}"
        self.entity_id = f"sensor.${DOMAIN}_${self._attr_unique_id}"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        new_value = self._extractor(self.coordinator.data)
        _LOGGER.debug("%s : %s", self._attr_unique_id, new_value)
        self._attr_native_value = new_value
        self.async_write_ha_state()


class BinarySensor(CoordinatorEntity[KomodoCoordinator], BinarySensorEntity):
    """Binary sensor."""

    def __init__(
        self,
        coordinator,
        extractor,
        category: str,
        key: str,
        id: str,
    ) -> None:
        """Initialize the sensor with the coordinator."""
        super().__init__(coordinator)
        self._extractor = extractor
        self._attr_translation_key = f"${category}_${key}"
        self._attr_has_entity_name = True
        self._attr_unique_id = f"${category}_${id}_${key}"
        self.entity_id = f"binary_sensor.${DOMAIN}_${self._attr_unique_id}"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        val = self._extractor(self.coordinator.data)
        _LOGGER.debug("%s : %s", self._attr_unique_id, val)
        self.is_on = val
        self.async_write_ha_state()
