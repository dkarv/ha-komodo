"""The BWT Perla integration."""

import logging

from custom_components.komodo import coordinator
from komodo_api.lib import ApiKeyInitOptions
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_API_KEY,
    CONF_API_SECRET,
    enabled_container_categories,
)
from .base import KomodoBase
from .sensors.container import container_sensor_category

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

    komodo.container_categories = enabled_container_categories(entry.options)
    hass.data[DOMAIN][entry.entry_id] = komodo
    await komodo.coordinator.async_config_entry_first_refresh()

    # Register the server devices up front, so the stack devices of all platforms
    # can reference them via their device registry id.
    device_reg = dr.async_get(hass)
    komodo.coordinator.server_device_ids = {
        server.id: device_reg.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, server.id)},
            name=server.name,
            manufacturer="Komodo",
            sw_version=server.periphery_version,
        ).id
        for server in komodo.coordinator.data.servers.values()
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_entry_updated))

    return True


async def _async_entry_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Enable or disable the container sensors of a category when its option changes.

    The listener also fires on reconfigure (data change), so only touch the
    categories whose option really changed - otherwise individually enabled
    container sensors would be disabled again.
    """
    komodo: KomodoBase = hass.data[DOMAIN][entry.entry_id]
    categories = enabled_container_categories(entry.options)
    changed = categories ^ komodo.container_categories
    if not changed:
        return

    entity_reg = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(entity_reg, entry.entry_id):
        category = container_sensor_category(entity.unique_id)
        if category not in changed:
            continue
        enabled = category in categories
        if enabled and entity.disabled_by == er.RegistryEntryDisabler.INTEGRATION:
            entity_reg.async_update_entity(entity.entity_id, disabled_by=None)
        elif not enabled and entity.disabled_by is None:
            entity_reg.async_update_entity(
                entity.entity_id, disabled_by=er.RegistryEntryDisabler.INTEGRATION
            )

    # Reload so newly created sensors pick up the new enabled default.
    await hass.config_entries.async_reload(entry.entry_id)


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
