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
from .coordinator import KomodoCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Komodo sensors from config entry."""
    my_api = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = KomodoCoordinator(hass, my_api)

    # Fetch initial data so we have data when entities subscribe
    #
    # If the refresh fails, async_config_entry_first_refresh will
    # raise ConfigEntryNotReady and setup will try again later
    #
    # If you do not want to retry setup on failure, use
    # coordinator.async_refresh() instead
    #
    #try:
    await coordinator.async_config_entry_first_refresh()
    # FIXME
    #except WrongCodeException as e:
    #    # Raising ConfigEntryAuthFailed will cancel future updates
    #    # and start a config flow with SOURCE_REAUTH (async_step_reauth)
    #    raise ConfigEntryAuthFailed from e

    entities = create_server_sensors(coordinator, config_entry.entry_id) + create_stack_sensors(coordinator, config_entry.entry_id) + create_alert_sensors(coordinator, config_entry.entry_id)

    async_add_entities(entities)
