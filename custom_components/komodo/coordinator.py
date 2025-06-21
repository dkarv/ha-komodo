"""Coordinator to fetch the data once for all sensors."""

import asyncio
import logging

from komodo_api.lib import KomodoClient
from komodo_api.types import ListServersResponse, ListStacksResponse, ListAlertsResponse, ListServers, ListStacks, ListAlerts

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

class KomodoData:
    servers: ListServersResponse
    stacks: ListStacksResponse
    alerts: ListAlertsResponse

    def __init__(self, servers: ListServersResponse, stacks: ListStacksResponse, alerts: ListAlertsResponse):
        self.servers = servers
        self.stacks = stacks
        self.alerts = alerts


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
