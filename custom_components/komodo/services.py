"""Services for the Komodo integration."""

import logging
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError

from komodo_api.types import (
    PruneSystem,
    PruneImages,
    PruneContainers,
    PruneVolumes,
    PruneBuildx,
    RestartAllContainers,
    GlobalAutoUpdate,
)

from .const import DOMAIN
from .base import KomodoBase
from .utils import wait_for_completion

_LOGGER = logging.getLogger(__name__)

SERVICE_PRUNE_DOCKER = "prune_docker"
SERVICE_RESTART_ALL_CONTAINERS = "restart_all_containers"
SERVICE_GLOBAL_AUTO_UPDATE = "global_auto_update"


def _get_komodo_instances(hass: HomeAssistant) -> list[KomodoBase]:
    """Get all loaded KomodoBase instances."""
    if DOMAIN not in hass.data:
        return []
    return [
        inst for inst in hass.data[DOMAIN].values()
        if isinstance(inst, KomodoBase)
    ]


def _resolve_server_id(komodo: KomodoBase, target: str) -> str:
    """Resolve server ID from server name or ID."""
    if komodo.coordinator and komodo.coordinator.data and komodo.coordinator.data.servers:
        if target in komodo.coordinator.data.servers:
            return target
        for srv in komodo.coordinator.data.servers.values():
            if srv.name == target:
                return srv.id
    return target


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register custom Komodo services."""

    async def handle_prune_docker(call: ServiceCall) -> None:
        """Handle docker pruning service call."""
        instances = _get_komodo_instances(hass)
        if not instances:
            raise HomeAssistantError("No active Komodo instances found.")

        target_server = call.data.get("server")
        prune_type = str(call.data.get("prune_type", "system")).lower()

        for komodo in instances:
            servers_to_prune: list[str] = []
            if target_server:
                servers_to_prune.append(_resolve_server_id(komodo, str(target_server)))
            elif komodo.coordinator and komodo.coordinator.data:
                servers_to_prune = [
                    s.id for s in komodo.coordinator.data.servers.values()
                    if s.id and not s.is_unknown
                ]

            for srv_id in servers_to_prune:
                _LOGGER.info("Pruning %s on server %s", prune_type, srv_id)
                if prune_type == "images":
                    update = await komodo.api.execute.pruneImages(PruneImages(server=srv_id))
                elif prune_type == "containers":
                    update = await komodo.api.execute.pruneContainers(PruneContainers(server=srv_id))
                elif prune_type == "volumes":
                    update = await komodo.api.execute.pruneVolumes(PruneVolumes(server=srv_id))
                elif prune_type == "buildx":
                    update = await komodo.api.execute.pruneBuildx(PruneBuildx(server=srv_id))
                else:
                    update = await komodo.api.execute.pruneSystem(PruneSystem(server=srv_id))

                await wait_for_completion(komodo.api, update, f"Prune {prune_type} on {srv_id}")

            if komodo.coordinator:
                await komodo.coordinator.async_request_refresh()

    async def handle_restart_all_containers(call: ServiceCall) -> None:
        """Handle restart all containers service call."""
        instances = _get_komodo_instances(hass)
        if not instances:
            raise HomeAssistantError("No active Komodo instances found.")

        target_server = call.data.get("server")
        if not target_server:
            raise HomeAssistantError("A target server must be specified.")

        for komodo in instances:
            srv_id = _resolve_server_id(komodo, str(target_server))
            _LOGGER.info("Restarting all containers on server %s", srv_id)
            update = await komodo.api.execute.restartAllContainers(
                RestartAllContainers(server=srv_id)
            )
            await wait_for_completion(komodo.api, update, f"Restart containers on {srv_id}")
            if komodo.coordinator:
                await komodo.coordinator.async_request_refresh()

    async def handle_global_auto_update(call: ServiceCall) -> None:
        """Handle global auto update service call."""
        instances = _get_komodo_instances(hass)
        if not instances:
            raise HomeAssistantError("No active Komodo instances found.")

        skip_auto_update = bool(call.data.get("skip_auto_update", False))
        for komodo in instances:
            _LOGGER.info("Triggering global auto update")
            update = await komodo.api.execute.globalAutoUpdate(
                GlobalAutoUpdate(skip_auto_update=skip_auto_update)
            )
            await wait_for_completion(komodo.api, update, "Global auto update")
            if komodo.coordinator:
                await komodo.coordinator.async_request_refresh()

    if not hass.services.has_service(DOMAIN, SERVICE_PRUNE_DOCKER):
        hass.services.async_register(DOMAIN, SERVICE_PRUNE_DOCKER, handle_prune_docker)

    if not hass.services.has_service(DOMAIN, SERVICE_RESTART_ALL_CONTAINERS):
        hass.services.async_register(DOMAIN, SERVICE_RESTART_ALL_CONTAINERS, handle_restart_all_containers)

    if not hass.services.has_service(DOMAIN, SERVICE_GLOBAL_AUTO_UPDATE):
        hass.services.async_register(DOMAIN, SERVICE_GLOBAL_AUTO_UPDATE, handle_global_auto_update)


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload Komodo services if no config entries remain."""
    if DOMAIN in hass.data and len(hass.data[DOMAIN]) > 0:
        return

    for service in (
        SERVICE_PRUNE_DOCKER,
        SERVICE_RESTART_ALL_CONTAINERS,
        SERVICE_GLOBAL_AUTO_UPDATE,
    ):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
