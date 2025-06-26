"""Example integration using DataUpdateCoordinator."""

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.entity import Entity
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..coordinator import KomodoCoordinator

_LOGGER = logging.getLogger(__name__)

class KomodoEntity(CoordinatorEntity[KomodoCoordinator], Entity):
    """Basic entity with common functionality."""

    def __init__(
        self,
        id,
        coordinator,
        extractor,
        category: str,
        key: str,
        name: str | None,
    ) -> None:
        """Initialize the common functionality."""
        super().__init__(coordinator)
        self._extractor = extractor
        self._attr_translation_key = f"${category}_${key}"
        self._attr_has_entity_name = True
        name_part = "" if name is None else f"_${name}"
        entity_id = f"${category}${name_part}_${key}"
        self.entity_id = f"sensor.${DOMAIN}_${entity_id}"
        self._attr_unique_id = f"${id}_${entity_id}"

class KomodoSensor(KomodoEntity, SensorEntity):
    """Basic sensor with common functionality."""

    def __init__(
        self,
        id,
        coordinator,
        extractor,
        category: str,
        key: str,
        name: str | None,
    ) -> None:
        """Initialize the sensor with the common coordinator."""
        KomodoEntity.__init__(self, id=id, coordinator=coordinator, extractor=extractor, category=category, key=key, name=name)
        self._attr_native_value = self._extractor(self.coordinator.data)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        new_value = self._extractor(self.coordinator.data)
        _LOGGER.debug("%s : %s", self._attr_unique_id, new_value)
        self._attr_native_value = new_value
        self.async_write_ha_state()


class KomodoBinarySensor(KomodoEntity, BinarySensorEntity):
    """Binary sensor."""

    def __init__(
        self,
        id,
        coordinator,
        extractor,
        category: str,
        key: str,
        name: str,
    ) -> None:
        """Initialize the sensor with the coordinator."""
        KomodoEntity.__init__(self, id=id, coordinator=coordinator, extractor=extractor, category=category, key=key, name=name)
        self.is_on = self._extractor(self.coordinator.data)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        val = self._extractor(self.coordinator.data)
        _LOGGER.debug("%s : %s", self._attr_unique_id, val)
        self.is_on = val
        self.async_write_ha_state()


class KomodoOptionSensor(KomodoSensor):
    """Option sensor."""

    def __init__(
        self,
        id,
        coordinator,
        extractor,
        category: str,
        key: str,
        name: str | None,
        options: list[str],
    ) -> None:
        """Initialize the parent sensor."""
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = options
        super().__init__(id=id, coordinator=coordinator, extractor=extractor, category=category, key=key, name=name)