from collections.abc import Awaitable, Callable

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from komodo_api.types import (
    RunAction,
    RunProcedure,
    DeployStack,
    RunBuild,
    Update,
)
from komodo_api.lib import KomodoClient

from custom_components.komodo.base import KomodoBase
from custom_components.komodo.const import DOMAIN
from custom_components.komodo.coordinator import KomodoCoordinator
from custom_components.komodo.utils import (
    wait_for_completion,
    create_stack_device_info,
    create_build_device_info,
    create_procedure_device_info,
    create_action_device_info,
)

import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    komodo: KomodoBase = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        create_procedure_buttons(komodo.coordinator, komodo.api, entry.entry_id)
        + create_action_buttons(komodo.coordinator, komodo.api, entry.entry_id)
        + create_deploy_buttons_for_stacks(
            komodo.coordinator, komodo.api, entry.entry_id
        )
        + create_build_buttons(komodo.coordinator, komodo.api, entry.entry_id)
    )


class KomodoExecuteButton(CoordinatorEntity[KomodoCoordinator], ButtonEntity):
    """Button that runs a Komodo execute action and waits for it to finish."""

    def __init__(
        self,
        coordinator: KomodoCoordinator,
        api: KomodoClient,
        unique_id: str,
        name: str,
        device_info: DeviceInfo,
        icon: str,
        action: Callable[[KomodoClient], Awaitable[Update]],
        enabled_default: bool = True,
    ) -> None:
        """Initialize the button entity."""
        super().__init__(coordinator)
        self._api = api
        self._action = action
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._attr_device_info = device_info
        self._attr_icon = icon
        self._attr_entity_registry_enabled_default = enabled_default

    async def async_press(self) -> None:
        """Run the action, wait for completion and refresh the coordinator."""
        _LOGGER.info("Starting %s", self._attr_name)
        try:
            update = await self._action(self._api)
            await wait_for_completion(self._api, update, self._attr_name)
            _LOGGER.info("Completed %s", self._attr_name)
            await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error("Failed %s: %s", self._attr_name, e)
            raise


def create_deploy_buttons_for_stacks(
    coordinator: KomodoCoordinator,
    api: KomodoClient,
    entry_id: str,
) -> list[KomodoExecuteButton]:
    """Create a deploy button for each stack."""
    return [
        KomodoExecuteButton(
            coordinator=coordinator,
            api=api,
            unique_id=f"{entry_id}_{stack.id}_deploy_button",
            name=f"Deploy {stack.name} stack",
            device_info=create_stack_device_info(
                stack, coordinator.server_device_ids, base_url=coordinator.host_url
            ),
            icon="mdi:rocket-launch",
            action=lambda api, sid=stack.id: api.execute.deployStack(
                DeployStack(stack=sid)
            ),
        )
        for stack in coordinator.data.stacks.values()
    ]


def create_build_buttons(
    coordinator: KomodoCoordinator,
    api: KomodoClient,
    entry_id: str,
) -> list[KomodoExecuteButton]:
    """Create a run button for each build (disabled by default)."""
    return [
        KomodoExecuteButton(
            coordinator=coordinator,
            api=api,
            unique_id=f"{entry_id}_{build.id}_run_button",
            name=f"Run {build.name} build",
            device_info=create_build_device_info(build, base_url=coordinator.host_url),
            icon="mdi:hammer-wrench",
            action=lambda api, bid=build.id: api.execute.runBuild(RunBuild(build=bid)),
            enabled_default=False,
        )
        for build in coordinator.data.builds.values()
    ]


def create_procedure_buttons(
    coordinator: KomodoCoordinator,
    api: KomodoClient,
    entry_id: str,
) -> list[KomodoExecuteButton]:
    """Create a run button for each procedure."""
    return [
        KomodoExecuteButton(
            coordinator=coordinator,
            api=api,
            # Unique id predates the shared button class; keep it so existing
            # procedure buttons are not orphaned.
            unique_id=f"{entry_id}_button_{procedure.id}",
            name=f"Run {procedure.name} procedure",
            device_info=create_procedure_device_info(
                procedure, base_url=coordinator.host_url
            ),
            icon="mdi:play-speed",
            action=lambda api, pid=procedure.id: api.execute.runProcedure(
                RunProcedure(procedure=pid)
            ),
        )
        for procedure in coordinator.data.procedures.values()
    ]


def create_action_buttons(
    coordinator: KomodoCoordinator,
    api: KomodoClient,
    entry_id: str,
) -> list[KomodoExecuteButton]:
    """Create a run button for each action (disabled by default)."""
    return [
        KomodoExecuteButton(
            coordinator=coordinator,
            api=api,
            unique_id=f"{entry_id}_{action.id}_run_button",
            name=f"Run {action.name} action",
            device_info=create_action_device_info(action, base_url=coordinator.host_url),
            icon="mdi:script-text-play",
            action=lambda api, aid=action.id: api.execute.runAction(
                RunAction(action=aid)
            ),
            enabled_default=False,
        )
        for action in coordinator.data.actions.values()
    ]
