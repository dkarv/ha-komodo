"""Coordinator to fetch the data once for all sensors."""

import asyncio
import logging
import time
from typing import Mapping

from komodo_api.types import InspectStackContainer, InspectStackContainerResponse

from komodo_api.lib import KomodoClient
from komodo_api.types import ListServersResponse, ListStacksResponse, ListAlertsResponse, ListServers, ListStacks, ListAlerts, ServerListItem, StackListItem

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Arrange servers into a mapping where the key is the name property
def arrange_servers_by_name(servers: ListServersResponse | None) -> Mapping[str, ServerListItem]:
    if servers is None:
        return {}
    return {server.name: server for server in servers if hasattr(server, "name")}

# Arrange stacks into a mapping where the key is the name property
def arrange_stacks_by_name(stacks: ListStacksResponse | None) -> Mapping[str, StackListItem]:
    if stacks is None:
        return {}
    return {stack.name: stack for stack in stacks if hasattr(stack, "name")}

class KomodoData:
    servers: Mapping[str, ServerListItem] | None
    stacks: Mapping[str, StackListItem] | None
    alerts: ListAlertsResponse | None
    # (stack, service) -> details
    services: Mapping[tuple[str, str], InspectStackContainerResponse] | None

    def __init__(self, 
                 servers: ListServersResponse | None, 
                 stacks: ListStacksResponse | None, 
                 alerts: ListAlertsResponse | None, 
                 services: Mapping[tuple[str, str], InspectStackContainerResponse] | None,
                 ):
        self.alerts = alerts
        self.servers = arrange_servers_by_name(servers)
        self.stacks = arrange_stacks_by_name(stacks)
        self.services = services


class KomodoCoordinator(DataUpdateCoordinator[KomodoData]):
    """Komodo coordinator."""

    def __init__(self, hass: HomeAssistant, my_api: KomodoClient) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="KomodoData",
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
                self.my_api.read.listServers(ListServers()),
                self.my_api.read.listStacks(ListStacks()),
                self.my_api.read.listAlerts(ListAlerts(
                    query = { 'resolved': False },
                )),
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            servers = responses[0] if not isinstance(responses[0], Exception) else None
            stacks = responses[1] if not isinstance(responses[1], Exception) else None
            alerts = responses[2] if not isinstance(responses[2], Exception) else None
            if servers is None:
                _LOGGER.error("Failed to fetch servers: %s", exc_info = responses[0])

            if stacks is None:
                _LOGGER.error("Failed to fetch stacks: %s", exc_info = responses[1])
                services_mapping = None
            else:
                services_mapping = await self._query_services(stacks)

            if alerts is None:
                _LOGGER.error("Failed to fetch alerts: %s", exc_info = responses[2])
            
            return KomodoData(servers, stacks, alerts, services_mapping)
    
    async def _query_services(self, stacks: ListStacksResponse) -> Mapping[tuple[str, str], InspectStackContainerResponse]:
        
        now = time.time()
        services_mapping = {}
        detail_tasks = {}

        # Check which services need to be queried
        for stack in stacks:
            for service in stack.info.services:
                if not service.update_available:
                    continue
                key = (stack.name, service.service)
                # Check if we have previous data and it's not older than 2 hours (7200 seconds)
                prev_data = None
                prev_time = None
                if self.data and self.data.services:
                    prev_data = self.data.services.get(key)
                    prev_time = self._service_timestamps.get(key)
                if prev_data and prev_time and (now - prev_time) < 7200:
                    services_mapping[key] = prev_data
                else:
                    _LOGGER.info(f"Fetching details for {key}")
                    detail_tasks[key] = self.my_api.read.inspectStackContainer(
                        InspectStackContainer(stack=stack.name, service=service.service)
                    )

        # Gather only the needed tasks
        if detail_tasks:
            service_results = await asyncio.gather(*detail_tasks.values())
            for key, result in zip(detail_tasks.keys(), service_results):
                services_mapping[key] = result
                self._service_timestamps[key] = now
        
        return services_mapping
