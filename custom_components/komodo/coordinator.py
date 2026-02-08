"""Coordinator to fetch the data once for all sensors."""

import asyncio
import logging
import time
from datetime import timedelta
from typing import Mapping

from komodo_api.types import InspectStackContainer, InspectStackContainerResponse

from komodo_api.lib import KomodoClient
from komodo_api.types import (
    ListServersResponse,
    ListStacksResponse,
    ListAlertsResponse,
    ListServers,
    ListStacks,
    ListAlerts,
    ServerListItem,
    StackListItem,
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .data.komodo_data import KomodoData
from .data.stack import KomodoUpdateInfo

_LOGGER = logging.getLogger(__name__)

class KomodoCoordinator(DataUpdateCoordinator[KomodoData]):
    """Komodo coordinator."""

    def __init__(self, hass: HomeAssistant, my_api: KomodoClient) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="KomodoData",
            update_interval=timedelta(minutes=5),
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
                services = await self._query_services(responses[1])
                data.add_stacks(responses[1], services)

            # Alerts
            if isinstance(responses[2], Exception):
                _LOGGER.error("Error fetching alerts", exc_info=responses[2])
            else:
                # TODO we currently only fetch the first page of alerts
                data.add_alerts(responses[2])

        return data

    async def _query_services(
        self, stacks: ListStacksResponse
    ) -> Mapping[str, Mapping[str, InspectStackContainerResponse]]:
        """Query details for all services that have updates available."""

        now = time.time()
        services_mapping = {}
        detail_tasks = {}

        # Check which services need to be queried
        for stack in stacks:
            services_mapping[stack.id] = {}
            for service in stack.info.services:
                if not service.update_available:
                    continue
                # Check if we have previous data and it's not older than 2 hours (7200 seconds)
                prev_data = None
                prev_time = None
                if self.data and self.data.services:
                    prev_data = self.data.services.get(stack.id, {}).get(service.service)
                    prev_time = self._service_timestamps.get((stack.id, service.service))
                if prev_data and prev_time and (now - prev_time) < 7200:
                    services_mapping[stack.id][service.service] = prev_data
                else:
                    _LOGGER.info("Fetching details for %s - %s", stack.id, service.service)
                    detail_tasks[(stack.id, service.service)] = self.my_api.read.inspectStackContainer(
                        InspectStackContainer(stack=stack.id, service=service.service)
                    )

        # Gather only the needed tasks
        if detail_tasks:
            service_results = await asyncio.gather(*detail_tasks.values())
            for (stack_id, service_name), result in zip(detail_tasks.keys(), service_results):
                services_mapping[stack_id][service_name] = KomodoUpdateInfo(result)
                self._service_timestamps[(stack_id, service_name)] = now

        return services_mapping
