"""Coordinator to fetch the data once for all sensors."""

import asyncio
import logging
from typing import Mapping

from komodo_api.lib import KomodoClient
from komodo_api.types import ListServersResponse, ListStacksResponse, ListAlertsResponse, ListServers, ListStacks, ListAlerts, ServerListItem, StackListItem

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Arrange servers into a mapping where the key is the name property
def arrange_servers_by_name(servers: ListServersResponse) -> Mapping[str, ServerListItem]:
    return {server.name: server for server in servers if hasattr(server, "name")}

# Arrange stacks into a mapping where the key is the name property
def arrange_stacks_by_name(stacks: ListStacksResponse) -> Mapping[str, StackListItem]:
    return {stack.name: stack for stack in stacks if hasattr(stack, "name")}

class KomodoData:
    servers: Mapping[str, ServerListItem]
    stacks: Mapping[str, StackListItem]
    alerts: ListAlertsResponse

    def __init__(self, servers: ListServersResponse, stacks: ListStacksResponse, alerts: ListAlertsResponse):
        self.alerts = alerts
        self.servers = arrange_servers_by_name(servers)
        self.stacks = arrange_stacks_by_name(stacks)


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
            responses = await asyncio.gather(*tasks)
            return KomodoData(responses[0], responses[1], responses[2])
