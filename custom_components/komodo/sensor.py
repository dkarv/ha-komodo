"""Example integration using DataUpdateCoordinator."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
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

    entities = (
        create_server_sensors(komodo.coordinator, entry.entry_id)
        + create_stack_sensors(komodo.coordinator, entry.entry_id)
        + create_alert_sensors(komodo.coordinator, entry.entry_id)
    )

    async_add_entities(entities)
