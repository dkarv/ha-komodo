"""Services for the Komodo integration."""

from collections.abc import Awaitable, Callable
import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr
from komodo_api.lib import KomodoClient
from komodo_api.types import (
    GlobalAutoUpdate,
    PruneBuildx,
    PruneContainers,
    PruneImages,
    PruneSystem,
    PruneVolumes,
    RestartAllContainers,
    Update,
)

from .base import KomodoBase
from .const import DOMAIN
from .utils import wait_for_completion

_LOGGER = logging.getLogger(__name__)

SERVICE_PRUNE_DOCKER = "prune_docker"
SERVICE_RESTART_ALL_CONTAINERS = "restart_all_containers"
SERVICE_GLOBAL_AUTO_UPDATE = "global_auto_update"

ATTR_SERVER = "server"
ATTR_PRUNE_TYPE = "prune_type"
ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_SKIP_AUTO_UPDATE = "skip_auto_update"

PRUNE_ACTIONS: dict[str, Callable[[KomodoClient, str], Awaitable[Update]]] = {
    "images": lambda api, s: api.execute.pruneImages(PruneImages(server=s)),
    "containers": lambda api, s: api.execute.pruneContainers(PruneContainers(server=s)),
    "volumes": lambda api, s: api.execute.pruneVolumes(PruneVolumes(server=s)),
    "buildx": lambda api, s: api.execute.pruneBuildx(PruneBuildx(server=s)),
    "system": lambda api, s: api.execute.pruneSystem(PruneSystem(server=s)),
}

SERVERS_SCHEMA = vol.All(cv.ensure_list, [cv.string], vol.Length(min=1))

PRUNE_DOCKER_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_SERVER): SERVERS_SCHEMA,
        vol.Required(ATTR_PRUNE_TYPE): vol.In(list(PRUNE_ACTIONS)),
    }
)
RESTART_ALL_CONTAINERS_SCHEMA = vol.Schema({vol.Required(ATTR_SERVER): SERVERS_SCHEMA})
GLOBAL_AUTO_UPDATE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional(ATTR_SKIP_AUTO_UPDATE, default=False): cv.boolean,
    }
)


def _komodo_for_entry(hass: HomeAssistant, entry_id: str) -> KomodoBase:
    """Return the loaded Komodo instance of a config entry."""
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        raise ServiceValidationError(f"{entry_id} is not a Komodo config entry")
    if entry.state is not ConfigEntryState.LOADED:
        raise ServiceValidationError(f"Komodo instance {entry.title} is not loaded")
    return hass.data[DOMAIN][entry_id]


def _resolve_servers(
    hass: HomeAssistant, device_ids: list[str]
) -> list[tuple[KomodoBase, str, str]]:
    """Map server device ids to (komodo instance, server id, server name)."""
    device_reg = dr.async_get(hass)
    targets = []
    for device_id in device_ids:
        device = device_reg.async_get(device_id)
        if device is None:
            raise ServiceValidationError(f"Unknown device {device_id}")
        for entry_id in device.config_entries:
            entry = hass.config_entries.async_get_entry(entry_id)
            if entry is None or entry.domain != DOMAIN:
                continue
            komodo = _komodo_for_entry(hass, entry_id)
            servers = komodo.coordinator.data.servers
            server = next(
                (
                    servers[ident]
                    for domain, ident in device.identifiers
                    if domain == DOMAIN and ident in servers
                ),
                None,
            )
            # Placeholder servers (see KomodoServer.unknown) have no state.
            if server is not None and server.state is not None:
                targets.append((komodo, server.id, server.name))
                break
        else:
            raise ServiceValidationError(
                f"Device {device.name_by_user or device.name} is not a Komodo server"
            )
    return targets


async def _run(
    komodo: KomodoBase,
    title: str,
    action: Callable[[KomodoClient], Awaitable[Update]],
) -> str | None:
    """Run a Komodo action to completion. Returns an error message on failure."""
    _LOGGER.info("Starting %s", title)
    try:
        update = await wait_for_completion(komodo.api, await action(komodo.api), title)
    except Exception as err:  # noqa: BLE001 - report every API failure to the caller
        _LOGGER.error("%s failed: %s", title, err)
        return f"{title}: {err}"
    if not update.success:
        return f"{title}: failed, see the Komodo logs"
    return None


async def _run_all(
    jobs: list[tuple[KomodoBase, str, Callable[[KomodoClient], Awaitable[Update]]]],
) -> None:
    """Run all jobs, refresh the affected instances and raise if any failed."""
    errors = [err for k, title, action in jobs if (err := await _run(k, title, action))]
    for komodo in {id(k): k for k, _, _ in jobs}.values():
        await komodo.coordinator.async_request_refresh()
    if errors:
        raise HomeAssistantError("; ".join(errors))


async def _handle_prune_docker(hass: HomeAssistant, call: ServiceCall) -> None:
    prune_type = call.data[ATTR_PRUNE_TYPE]
    prune = PRUNE_ACTIONS[prune_type]
    await _run_all(
        [
            (komodo, f"Prune {prune_type} on {name}", lambda api, s=srv_id: prune(api, s))
            for komodo, srv_id, name in _resolve_servers(hass, call.data[ATTR_SERVER])
        ]
    )


async def _handle_restart_all_containers(hass: HomeAssistant, call: ServiceCall) -> None:
    await _run_all(
        [
            (
                komodo,
                f"Restart all containers on {name}",
                lambda api, s=srv_id: api.execute.restartAllContainers(
                    RestartAllContainers(server=s)
                ),
            )
            for komodo, srv_id, name in _resolve_servers(hass, call.data[ATTR_SERVER])
        ]
    )


async def _handle_global_auto_update(hass: HomeAssistant, call: ServiceCall) -> None:
    komodo = _komodo_for_entry(hass, call.data[ATTR_CONFIG_ENTRY_ID])
    skip = call.data[ATTR_SKIP_AUTO_UPDATE]
    await _run_all(
        [
            (
                komodo,
                "Global auto update",
                lambda api: api.execute.globalAutoUpdate(
                    GlobalAutoUpdate(skip_auto_update=skip)
                ),
            )
        ]
    )


def async_setup_services(hass: HomeAssistant) -> None:
    """Register the Komodo services (once, from async_setup)."""
    for service, handler, schema in (
        (SERVICE_PRUNE_DOCKER, _handle_prune_docker, PRUNE_DOCKER_SCHEMA),
        (
            SERVICE_RESTART_ALL_CONTAINERS,
            _handle_restart_all_containers,
            RESTART_ALL_CONTAINERS_SCHEMA,
        ),
        (SERVICE_GLOBAL_AUTO_UPDATE, _handle_global_auto_update, GLOBAL_AUTO_UPDATE_SCHEMA),
    ):

        async def _call(call: ServiceCall, handler=handler) -> None:
            await handler(hass, call)

        hass.services.async_register(DOMAIN, service, _call, schema=schema)
