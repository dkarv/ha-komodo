"""Coordinator to fetch the data once for all sensors."""

import asyncio
import logging
import time
from datetime import timedelta
from functools import partial

from komodo_api.exceptions import KomodoException
from komodo_api.types import InspectStackContainer, InspectStackContainerResponse

from komodo_api.lib import KomodoClient
from komodo_api.types import (
    ListServers,
    ListStacks,
    ListAlerts,
    GetSystemStats,
)

from releaseprobe import check_for_update

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .data.komodo_data import KomodoData
from .data.stack import KomodoStack
from .data.service import KomodoService, KomodoUpdateInfo

_LOGGER = logging.getLogger(__name__)
_RELEASEPROBE_LOGGER = _LOGGER.getChild("releaseprobe")

# Substring of the error Komodo core returns when a stack has no container for
# the service (see bin/core/src/api/read/stack.rs). The core sends it with the
# default HTTP 500, so the message text is the only way to tell it apart from a
# genuine internal error.
_NO_CONTAINER_ERROR = "No service found matching"


class KomodoCoordinator(DataUpdateCoordinator[KomodoData]):
    """Komodo coordinator."""

    def __init__(self, hass: HomeAssistant, my_api: KomodoClient) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="KomodoData",
            update_interval=timedelta(minutes=1),
        )
        self.my_api = my_api
        self._service_timestamps: dict[tuple[str, str], float] = {}

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        # Note: asyncio.TimeoutError and aiohttp.ClientError are already
        # handled by the data update coordinator.
        async with asyncio.timeout(10):
            tasks = [
                # limit=0 disables Komodo's default pagination (30 items per
                # page), so all resources are returned in a single response.
                self.my_api.read.listServers(ListServers(limit=0)),
                self.my_api.read.listStacks(ListStacks(limit=0)),
                self.my_api.read.listAlerts(
                    ListAlerts(
                        query={"resolved": False},
                    )
                ),
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            _LOGGER.debug("Server response: %s", responses[0])
            _LOGGER.debug("Stack response: %s", responses[1])
            _LOGGER.debug("Alert response: %s", responses[2])
            data = KomodoData()

            # Servers
            if isinstance(responses[0], Exception):
                _LOGGER.error("Error fetching servers", exc_info=responses[0])
            else:
                data.add_servers(responses[0])

            # Stacks
            if isinstance(responses[1], Exception):
                _LOGGER.error("Error fetching stacks", exc_info=responses[1])
            else:
                data.add_stacks(responses[1])

            # Alerts
            if isinstance(responses[2], Exception):
                _LOGGER.error("Error fetching alerts", exc_info=responses[2])
            else:
                # TODO we currently only fetch the first page of alerts
                data.add_alerts(responses[2])

        await self._compute_update_info(data)
        await self._fetch_service_states(data)
        await self._fetch_server_stats(data)
        return data

    async def _fetch_server_stats(self, data: KomodoData):
        """Fetch cpu/memory/disk/load stats for all servers.

        Komodo core keeps these stats up to date by polling periphery
        servers on its own schedule, so this reads from that cache
        instead of triggering a live query per server.
        """

        async def fetch_one(server_id: str) -> None:
            try:
                stats = await self.my_api.read.getSystemStats(
                    GetSystemStats(server=server_id)
                )
            except KomodoException as e:
                _LOGGER.debug(
                    "Failed to get system stats for server %s: %s", server_id, e.error
                )
                return
            except Exception as e:
                _LOGGER.error(
                    "Failed to get system stats for server %s: %s", server_id, e
                )
                return
            data.get_server(server_id).set_stats(stats)

        await asyncio.gather(*(fetch_one(server_id) for server_id in data.servers))

    async def _compute_update_info(self, new_data: KomodoData):
        """Compute update info for services."""
        for stack_id, stack in new_data.stacks.items():
            previous_stack = self.data.stacks.get(stack_id) if self.data else None
            for service_id, service in stack.services.items():
                previous_service = previous_stack.services.get(service_id) if previous_stack else None
                await self._inspect_service_if_needed(stack, service, stack_id, previous_service)

    async def _inspect_service_if_needed(
        self,
        stack: KomodoStack,
        service: KomodoService,
        stack_id: str,
        previous_service: KomodoService | None,
    ) -> None:
        if not service.update_available:
            return

        now = time.time()
        previous_update_info = previous_service.update_info if previous_service else None
        if (
            previous_update_info
            and (now - previous_update_info.info_updated_at) < 7200
        ):
            service.update_info = previous_update_info
        elif stack.has_inspectable_container:
            await self._inspect_service(service, stack_id, now)
        else:
            # No container to inspect (stack DOWN/UNKNOWN). Carry any cached
            # update info forward so a pending update isn't lost while the
            # stack is down and reported as installed=0/latest=0.
            service.update_info = previous_update_info

    async def _fetch_service_states(self, data: KomodoData):
        """Fetch service states for all services."""
        tasks = []
        for stack_id, stack in data.stacks.items():
            if not stack.has_inspectable_container:
                continue
            for service in stack.services.values():
                if service.state is None:
                    tasks.append(self._inspect_service(service, stack_id, time.time()))
        await asyncio.gather(*tasks)

    async def _inspect_service(self, service: KomodoService, stack_id: str, updated_at: float):
        """Inspect a service to get update info."""
        try:
            response = await self.my_api.read.inspectStackContainer(
                InspectStackContainer(stack=stack_id, service=service.name)
            )
            _LOGGER.debug("Inspecting service %s in stack %s: %s", service.name, stack_id, response)
        except KomodoException as e:
            if _NO_CONTAINER_ERROR in e.error:
                # Expected when a stack in a state we didn't guard against
                # (e.g. UNHEALTHY, a partial deploy, or a service removed from
                # the compose file) has no container for this service.
                _LOGGER.debug(
                    "No container to inspect for service %s in stack %s: %s",
                    service.name, stack_id, e.error,
                )
            else:
                _LOGGER.error(
                    "Failed to inspect service %s in stack %s: %s",
                    service.name, stack_id, e.error,
                )
            return
        except Exception as e:
            _LOGGER.error("Failed to inspect service %s in stack %s: %s", service.name, stack_id, e)
            return
        service.state = response.state
        if service.update_available and service.update_info is None:
            update_info = KomodoUpdateInfo(response, updated_at)
            await self._probe_release_info(update_info, response)
            service.update_info = update_info

    async def _probe_release_info(
        self, update_info: KomodoUpdateInfo, response: InspectStackContainerResponse
    ) -> None:
        """Query releaseprobe for the real new version and release notes."""
        if not response.config or not response.config.image:
            return
        try:
            # Passing the container's own labels lets releaseprobe resolve
            # the current version for floating tags (e.g. `latest`) and
            # skips a redundant registry round-trip for pinned ones.
            check = await self.hass.async_add_executor_job(
                partial(
                    check_for_update,
                    response.config.image,
                    response.config.labels or {},
                    logger=_RELEASEPROBE_LOGGER,
                )
            )
        except Exception as e:
            _LOGGER.debug(
                "releaseprobe failed for image %s: %s", response.config.image, e
            )
            return
        update_info.apply_release_info(check)
