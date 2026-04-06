"""The BWT Perla integration."""

import logging

from custom_components.komodo import coordinator
from komodo_api.lib import ApiKeyInitOptions
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import DOMAIN, CONF_HOST, CONF_API_KEY, CONF_API_SECRET
from .base import KomodoBase

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.UPDATE, Platform.BUTTON, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Komodo from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    komodo = KomodoBase(
        hass,
        entry.data[CONF_HOST],
        ApiKeyInitOptions(entry.data[CONF_API_KEY], entry.data[CONF_API_SECRET]),
    )
    try:
        await komodo.test_connection()
    except Exception as e:
        _LOGGER.exception("Error setting up Komodo API: {e}")
        await komodo.close()
        raise ConfigEntryNotReady from e

    hass.data[DOMAIN][entry.entry_id] = komodo
    await komodo.coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        komodo = hass.data[DOMAIN].pop(entry.entry_id)
        await komodo.close()

    return unload_ok

async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Allow removing a device (stack) from the UI."""
    entity_reg = er.async_get(hass)
    entities = er.async_entries_for_device(
        entity_reg,
        device_entry.id,
        include_disabled_entities=True,
    )
    return not any(
        entity.config_entry_id == config_entry.entry_id for entity in entities
    )
