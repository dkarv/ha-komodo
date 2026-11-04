"""Coordinator to fetch the data once for all sensors."""

from typing import Any
import asyncio
import logging
import time
from datetime import timedelta
from functools import partial

from komodo_api.exceptions import KomodoException
from komodo_api.lib import KomodoClient
from komodo_api.types import (
    InspectStackContainer,
    ListActions,
    ListAlerts,
    ListAllStackServices,
    ListBuilds,
    ListProcedures,
    ListServers,
    ListStacks,
)

from releaseprobe import UnknownVersionError, check_for_update
from releaseprobe.imageref import parse
from releaseprobe.registry import fetch_labels

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .data.komodo_data import KomodoData
from .data.service import KomodoService, KomodoUpdateInfo
from .utils import derive_changelog_url

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
        self.host_url: str | None = None
        self.komodo_version: str | None = None
        # Komodo server id -> device registry id, filled in during entry setup.
        self.server_device_ids: dict[str, str] = {}

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
                # Builds (CI/CD pipelines)
                self.my_api.read.listBuilds(ListBuilds(limit=0)),
                # Procedures & Actions (Runbooks & Automations)
                self.my_api.read.listProcedures(ListProcedures(limit=0)),
                self.my_api.read.listActions(ListActions(limit=0)),
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            _LOGGER.debug("Server response: %s", responses[0])
            _LOGGER.debug("Stack response: %s", responses[1])
            _LOGGER.debug("Alert response: %s", responses[2])
            _LOGGER.debug("Stack services response: %s", responses[3])
            _LOGGER.debug("Build response: %s", responses[4])
            _LOGGER.debug("Procedure response: %s", responses[5])
            _LOGGER.debug("Action response: %s", responses[6])
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

            # Builds (CI/CD)
            if len(responses) > 4 and not isinstance(responses[4], Exception):
                data.add_builds(responses[4])
            elif len(responses) > 4 and isinstance(responses[4], Exception):
                _LOGGER.debug("Error fetching builds: %s", responses[4])

            # Procedures
            if len(responses) > 5 and not isinstance(responses[5], Exception):
                data.add_procedures(responses[5])
            elif len(responses) > 5 and isinstance(responses[5], Exception):
                _LOGGER.debug("Error fetching procedures: %s", responses[5])

            # Actions
            if len(responses) > 6 and not isinstance(responses[6], Exception):
                data.add_actions(responses[6])
            elif len(responses) > 6 and isinstance(responses[6], Exception):
                _LOGGER.debug("Error fetching actions: %s", responses[6])

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
                    update_info = KomodoUpdateInfo(now, current_version=service.installed_version)
                    service.update_info = update_info
                    self._schedule_release_probe(update_info, stack_id, service)
                else:
                    # No container (stack DOWN/UNKNOWN). Carry any cached
                    # update info forward so a pending update isn't lost while
                    # the stack is down.
                    service.update_info = previous_update_info

    def _schedule_release_probe(
        self, update_info: KomodoUpdateInfo, stack_id: str, service: KomodoService
    ) -> None:
        """Kick off the container inspect + releaseprobe lookup in the background.

        The inspect is needed for container labels, environment variables,
        and configured image tags. Running it as a background task keeps it off
        the coordinator's update cycle.
        """
        self.hass.async_create_background_task(
            self._async_probe_release_info(update_info, stack_id, service),
            name=f"komodo_release_probe_{service.name}",
        )

    async def _async_probe_release_info(
        self, update_info: KomodoUpdateInfo, stack_id: str, service: KomodoService
    ) -> None:
        """Inspect the container, run the release probe, and notify entities."""
        info = await self._fetch_container_inspect(stack_id, service.name)
        labels = info.get("labels", {})
        env = info.get("env", [])
        config_image = info.get("config_image")

        service.labels = labels
        service.env = env
        if config_image:
            service.config_image = config_image

        update_info.apply_labels(labels)
        update_info.apply_env(env, service_name=service.name)
        self.async_update_listeners()

        stack = self.data.stacks.get(stack_id) if self.data else None
        stack_repo_link = getattr(stack, "repo_link", None) if stack else None

        effective_img = service.effective_image
        if effective_img and not effective_img.startswith("sha256:"):
            await self._probe_release_info(
                update_info,
                effective_img,
                labels,
                digests=service.image_digests,
                stack_repo_link=stack_repo_link,
            )

        # Fallback for release_url: dynamically derive changelog URL if not found by releaseprobe
        if not update_info.release_url:
            update_info.release_url = derive_changelog_url(
                image=effective_img or service.image,
                labels=labels,
                stack_repo_link=stack_repo_link,
                version=update_info.new_version or update_info.current_version,
            )

        # Ensure installed_version is never "0" if we know the container's version/tag
        if not update_info.current_version or update_info.current_version == "0":
            installed = service.installed_version
            if installed and installed != "0":
                update_info.current_version = installed

        # If new_version is still missing or identical to current_version while an update is pending
        if service.update_available and (not update_info.new_version or update_info.new_version == update_info.current_version):
            if update_info.current_version and update_info.current_version != "0":
                update_info.new_version = f"{update_info.current_version} (update available)"
            else:
                update_info.new_version = "update available"

        self.async_update_listeners()

    async def _fetch_container_inspect(self, stack_id: str, service_name: str) -> dict[str, Any]:
        """Get the full inspect data of a service's container."""
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

        config = response.config if response else None
        return {
            "labels": (config.labels if config else None) or {},
            "env": (config.env if config else None) or [],
            "config_image": (config.image if config else None) or "",
            "image_id": getattr(response, "image", None) or "",
            "created": getattr(response, "created", None) or "",
        }

    async def _fetch_container_labels(self, stack_id: str, service_name: str) -> dict[str, str]:
        """Get the labels of a service's container (backwards compatibility)."""
        info = await self._fetch_container_inspect(stack_id, service_name)
        return info.get("labels", {})

    async def _probe_release_info(
        self,
        update_info: KomodoUpdateInfo,
        image: str,
        labels: dict[str, str],
        digests: list[str] | None = None,
        stack_repo_link: str | None = None,
    ) -> None:
        """Query releaseprobe for the real new version and release notes."""
        if not image or image.startswith("sha256:"):
            return

        check = None
        try:
            check = await self.hass.async_add_executor_job(
                partial(
                    check_for_update,
                    image,
                    current_labels=labels,
                    current_digests=digests or None,
                    logger=_RELEASEPROBE_LOGGER,
                )
            )
        except UnknownVersionError:
            _LOGGER.debug(
                "Cannot determine installed version of %s from tags list: image uses a floating tag",
                image,
            )
        except Exception as e:
            _LOGGER.debug(
                "Failed to look up the new version and release notes for %s: %s", image, e
            )

        if check:
            update_info.apply_release_info(check)

        # If latest_version is still unset or "update available" (e.g. tag updated in-place on Docker Hub),
        # probe registry labels directly for the configured tag
        if update_info.new_version in ("update available", "0", None) or not update_info.release_url:
            try:
                ref = parse(image)
                reg_labels = await self.hass.async_add_executor_job(
                    partial(fetch_labels, ref, logger=_RELEASEPROBE_LOGGER)
                )
                if reg_labels:
                    update_info.apply_registry_labels(
                        reg_labels,
                        image=image,
                        stack_repo_link=stack_repo_link,
                    )
            except Exception as e:
                _LOGGER.debug("Failed to fetch registry labels for %s: %s", image, e)
