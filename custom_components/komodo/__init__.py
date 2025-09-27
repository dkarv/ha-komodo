"""The BWT Perla integration."""

import logging

from komodo_api.lib import ApiKeyInitOptions
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, CONF_HOST, CONF_API_KEY, CONF_API_SECRET
from .base import KomodoBase

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.UPDATE, Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Komodo from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    komodo = KomodoBase(hass, entry.data[CONF_HOST], ApiKeyInitOptions(entry.data[CONF_API_KEY], entry.data[CONF_API_SECRET]))
    try:
        await komodo.test_connection()
    except Exception as e:
        _LOGGER.exception("Error setting up Komodo API: {e}")
        await komodo.close()
        raise ConfigEntryNotReady from e

    hass.data[DOMAIN][entry.entry_id] = komodo

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        komodo = hass.data[DOMAIN].pop(entry.entry_id)
        await komodo.close()

    return unload_ok
