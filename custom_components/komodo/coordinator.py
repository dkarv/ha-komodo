"""Coordinator to fetch the data once for all sensors."""

import asyncio
import logging
import time
from datetime import timedelta
from typing import List

from komodo_api.types import InspectStackContainer, InspectStackContainerResponse

from komodo_api.lib import KomodoClient
from komodo_api.types import (
    ListServersResponse,
    ListStacksResponse,
    ListAlertsResponse,
    ListServers,
    ListStacks,
    ListAlerts,
    ListStackServices,
    ServerListItem,
    StackListItem,
    StackService,
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .data.komodo_data import KomodoData
from .data.stack import  KomodoStack
from .data.service import KomodoService, KomodoUpdateInfo

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
                data.add_stacks(responses[1])

            # Alerts
            if isinstance(responses[2], Exception):
                _LOGGER.error("Error fetching alerts", exc_info=responses[2])
            else:
                # TODO we currently only fetch the first page of alerts
                data.add_alerts(responses[2])

        # Fetch details for services
        await self._list_services(data)
        return data
    
    async def _list_services(self, data: KomodoData):
        """Fetch services for each stack."""
        tasks = {}
        for stack_id in data.stacks.keys():
            tasks[stack_id] = self.my_api.read.listStackServices(ListStackServices(stack=stack_id))
        
        if tasks:
            responses = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for stack_id, response in zip(tasks.keys(), responses):
                if isinstance(response, Exception):
                    _LOGGER.error("Error fetching services for stack %s", stack_id, exc_info=response)
                else:
                    previous_stack = self.data.stacks[stack_id] if self.data else None
                    services = await self._inspect_services_if_needed(response, stack_id, previous_stack)
                    data.add_services(stack_id, services)
    
    async def _inspect_services_if_needed(self, services: List[StackService], stack_id: str, previous_stack: KomodoStack | None) -> list[KomodoService]:
        infos = []
        now = time.time()
        for service in services:
            if not service.update_available:
                infos.append(KomodoService(service))
            else:
                previous_service = previous_stack.services.get(service.service) if previous_stack else None
                previous_update_info = previous_service.update_info if previous_service else None
                if previous_update_info and (now - previous_update_info.info.info_updated_at) < 7200:
                    infos.append(KomodoService(service, previous_update_info))
                else:
                    _LOGGER.debug("Inspecting service %s in stack %s for update", service.service, stack_id)
                    response = await self.my_api.read.inspectStackContainer(InspectStackContainer(stack=stack_id, service=service.service))
                    infos.append(KomodoService(service, KomodoUpdateInfo(response, now)))
        return infos
