"""The BWT Perla integration."""

import logging

from komodo_api import KomodoClient, ApiKeyInitOptions
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity_registry import async_migrate_entries

from .const import DOMAIN, CONF_HOST, CONF_API_KEY, CONF_API_SECRET

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.UPDATE]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Komodo from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    api = await KomodoClient(entry.data[CONF_HOST], ApiKeyInitOptions(entry.data[CONF_API_KEY], entry.data[CONF_API_SECRET]))
    try:
        await api.read.getVersion()
    except Exception as e:
        _LOGGER.exception("Error setting up Komodo API")
        await api.close()
        raise ConfigEntryNotReady from e

    hass.data[DOMAIN][entry.entry_id] = api

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        api = hass.data[DOMAIN].pop(entry.entry_id)
        await api.close()

    return unload_ok
