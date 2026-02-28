"""Example integration using DataUpdateCoordinator."""

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.entity import Entity
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from ..const import DOMAIN
from ..coordinator import KomodoCoordinator

_LOGGER = logging.getLogger(__name__)


class KomodoEntity(CoordinatorEntity[KomodoCoordinator], Entity):
    """Basic entity with common functionality."""

    def __init__(
        self,
        item_id,
        coordinator,
        extractor,
        key: str,
        device_info: DeviceInfo | None,
    ) -> None:
        """Initialize the common functionality."""
        super().__init__(coordinator)
        self._extractor = extractor
        self._attr_translation_key = key
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{item_id}_{key}"
        self._attr_device_info = device_info


class KomodoSensor(KomodoEntity, SensorEntity):
    """Basic sensor with common functionality."""

    def __init__(
        self,
        item_id,
        coordinator,
        extractor,
        key: str,
        device_info: DeviceInfo | None = None,
    ) -> None:
        """Initialize the sensor with the common coordinator."""
        KomodoEntity.__init__(
            self,
            item_id=item_id,
            coordinator=coordinator,
            extractor=extractor,
            key=key,
            device_info=device_info,
        )
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
        item_id,
        coordinator,
        extractor,
        key: str,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the sensor with the coordinator."""
        KomodoEntity.__init__(
            self,
            item_id=item_id,
            coordinator=coordinator,
            extractor=extractor,
            key=key,
            device_info=device_info,
        )
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
        item_id,
        coordinator,
        extractor,
        key: str,
        device_info: DeviceInfo,
        options: list[str],
    ) -> None:
        """Initialize the parent sensor."""
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = options
        super().__init__(
            item_id=item_id,
            coordinator=coordinator,
            extractor=extractor,
            key=key,
            device_info=device_info,
        )
