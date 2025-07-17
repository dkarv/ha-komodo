"""Example integration using DataUpdateCoordinator."""

from datetime import datetime
import logging
from zoneinfo import ZoneInfo

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfMass,
    UnitOfTime,
    UnitOfVolume,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .sensors.alert import create_alert_sensors
from .sensors.server import create_server_sensors
from .sensors.stack import create_stack_sensors

from .const import DOMAIN
from .base import KomodoBase

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Komodo sensors from config entry."""
    komodo: KomodoBase = hass.data[DOMAIN][entry.entry_id]

    await komodo.first_refresh()
    # FIXME catch invalid auth exception and raise ConfigEntryAuthFailed

    entities = (
        create_server_sensors(komodo.coordinator, entry.entry_id) + 
        create_stack_sensors(komodo.coordinator, entry.entry_id) + 
        create_alert_sensors(komodo.coordinator, entry.entry_id)
    )

    async_add_entities(entities)
