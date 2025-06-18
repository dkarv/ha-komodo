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
    try:
        await coordinator.async_config_entry_first_refresh()
        # FIXME
    except WrongCodeException as e:
        # Raising ConfigEntryAuthFailed will cancel future updates
        # and start a config flow with SOURCE_REAUTH (async_step_reauth)
        raise ConfigEntryAuthFailed from e

    # FIXME look into device info
    device_info = DeviceInfo(
        configuration_url=None,
        connections=set(),
        entry_type=None,
        hw_version=None,
        identifiers={(DOMAIN, config_entry.entry_id)},
        manufacturer="BWT",
        model=f'Perla {model_suffix}',
        name=config_entry.title,
        serial_number=None,
        suggested_area=None,
        sw_version=coordinator.data.firmware_version,
        via_device=None,
    )

    entities = []

    async_add_entities(entities)
