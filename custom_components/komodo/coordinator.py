"""Coordinator to fetch the data once for all sensors."""

import asyncio
import logging
import time
from datetime import timedelta
from functools import partial

from komodo_api.exceptions import KomodoException
from komodo_api.lib import KomodoClient
from komodo_api.types import (
    InspectStackContainer,
    ListServers,
    ListStacks,
    ListAlerts,
    ListAllStackServices,
)

from releaseprobe import check_for_update

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .data.komodo_data import KomodoData
from .data.service import KomodoService, KomodoUpdateInfo

_LOGGER = logging.getLogger(__name__)
_RELEASEPROBE_LOGGER = _LOGGER.getChild("releaseprobe")


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
                # Container state, image and labels for every stack service,
                # from core's cached container list - one call instead of an
                # inspectStackContainer (live periphery query) per service.
                self.my_api.read.listAllStackServices(ListAllStackServices(limit=0)),
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            _LOGGER.debug("Server response: %s", responses[0])
            _LOGGER.debug("Stack response: %s", responses[1])
            _LOGGER.debug("Alert response: %s", responses[2])
            _LOGGER.debug("Stack services response: %s", responses[3])
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

            # Stack services (needs stacks added first)
            if isinstance(responses[3], Exception):
                _LOGGER.error("Error fetching stack services", exc_info=responses[3])
            else:
                data.add_stack_services(responses[3])

        self._compute_update_info(data)
        return data

    def _compute_update_info(self, new_data: KomodoData):
        """Compute update info for services with a pending update."""
        now = time.time()
        for stack_id, stack in new_data.stacks.items():
            previous_stack = self.data.stacks.get(stack_id) if self.data else None
            for service_id, service in stack.services.items():
                if not service.update_available:
                    continue
                previous_service = previous_stack.services.get(service_id) if previous_stack else None
                previous_update_info = previous_service.update_info if previous_service else None
                if (
                    previous_update_info
                    and (now - previous_update_info.info_updated_at) < 7200
                ):
                    service.update_info = previous_update_info
                elif service.has_container:
                    update_info = KomodoUpdateInfo(now)
                    service.update_info = update_info
                    self._schedule_release_probe(update_info, stack_id, service)
                else:
                    # No container (stack DOWN/UNKNOWN). Carry any cached
                    # update info forward so a pending update isn't lost while
                    # the stack is down and reported as installed=0/latest=0.
                    service.update_info = previous_update_info

    def _schedule_release_probe(
        self, update_info: KomodoUpdateInfo, stack_id: str, service: KomodoService
    ) -> None:
        """Kick off the container inspect + releaseprobe lookup in the background.

        The inspect is needed for the container labels (list items don't carry
        them), and is a live periphery query. releaseprobe hits external registries and (for GitHub-hosted images) the GitHub
        API to resolve the real new version and changelog, which can be slow
        or rate-limited. Running it as a background task keeps it off the
        coordinator's update cycle - and, on the first update, off config
        entry setup - so a slow/unreachable registry can't cause a setup
        timeout. update_info starts with placeholder values and is mutated
        in place once the probe completes; _compute_update_info carries the
        same object forward across refreshes (see its cache check), so the
        update is picked up regardless of which refresh is current by the
        time it lands.
        """
        self.hass.async_create_background_task(
            self._async_probe_release_info(update_info, stack_id, service.name, service.image),
            name=f"komodo_release_probe_{service.name}",
        )

    async def _async_probe_release_info(
        self, update_info: KomodoUpdateInfo, stack_id: str, service_name: str, image: str
    ) -> None:
        """Inspect the container, run the release probe, and notify entities."""
        labels = await self._fetch_container_labels(stack_id, service_name)
        update_info.apply_labels(labels)
        self.async_update_listeners()
        await self._probe_release_info(update_info, image, labels)
        self.async_update_listeners()

    async def _fetch_container_labels(self, stack_id: str, service_name: str) -> dict[str, str]:
        """Get the labels of a service's container (including image labels)."""
        try:
            async with asyncio.timeout(10):
                response = await self.my_api.read.inspectStackContainer(
                    InspectStackContainer(stack=stack_id, service=service_name)
                )
        except KomodoException as e:
            _LOGGER.debug(
                "Failed to inspect service %s in stack %s: %s", service_name, stack_id, e.error
            )
            return {}
        except Exception as e:
            _LOGGER.debug(
                "Failed to inspect service %s in stack %s: %s", service_name, stack_id, e
            )
            return {}
        return (response.config.labels if response.config else None) or {}

    async def _probe_release_info(
        self, update_info: KomodoUpdateInfo, image: str, labels: dict[str, str]
    ) -> None:
        """Query releaseprobe for the real new version and release notes."""
        if not image:
            return
        try:
            # Passing the container's own labels lets releaseprobe resolve
            # the current version for floating tags (e.g. `latest`) and
            # skips a redundant registry round-trip for pinned ones.
            check = await self.hass.async_add_executor_job(
                partial(
                    check_for_update,
                    image,
                    labels,
                    logger=_RELEASEPROBE_LOGGER,
                )
            )
        except Exception as e:
            _LOGGER.debug(
                "releaseprobe failed for image %s: %s", image, e
            )
            return
        update_info.apply_release_info(check)
