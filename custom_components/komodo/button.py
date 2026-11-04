from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from komodo_api.types import (
    RunProcedure,
    RunAction,
    DeployStack,
    RunBuild,
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

    # Procedure buttons (disabled by default)
    procedure_entities = create_procedure_buttons(
        komodo.coordinator, komodo.api, entry.entry_id
    )

    # Action buttons (disabled by default)
    action_entities = create_action_buttons(
        komodo.coordinator, komodo.api, entry.entry_id
    )

    # Stack deploy buttons
    deploy_entities = create_deploy_buttons_for_stacks(
        komodo.coordinator, komodo.api, entry.entry_id
    )

    # Build run buttons (disabled by default)
    build_entities = create_build_buttons(
        komodo.coordinator, komodo.api, entry.entry_id
    )

    async_add_entities(
        procedure_entities + action_entities + deploy_entities + build_entities
    )


class KomodoProcedureButton(CoordinatorEntity[KomodoCoordinator], ButtonEntity):
    """Button entity to run a procedure runbook."""

    _attr_entity_registry_enabled_default = False
    _attr_icon = "mdi:play-speed"

    def __init__(
        self,
        coordinator: KomodoCoordinator,
        api: KomodoClient,
        item_id: str,
        procedure_id: str,
        procedure_name: str,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the procedure button entity."""
        super().__init__(coordinator)
        self._api = api
        self._procedure_id = procedure_id
        self._procedure_name = procedure_name
        self._attr_unique_id = f"{item_id}_run_button"
        self._attr_device_info = device_info
        self._attr_name = f"Run {procedure_name} procedure"

    async def async_press(self) -> None:
        """Trigger the procedure."""
        _LOGGER.info("Starting procedure %s", self._procedure_name)
        try:
            update = await self._api.execute.runProcedure(
                RunProcedure(procedure=self._procedure_id)
            )
            update = await wait_for_completion(
                self._api, update, f"Procedure {self._procedure_name}"
            )
            _LOGGER.info("Completed procedure %s", self._procedure_name)
            await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error("Failed to run procedure %s: %s", self._procedure_name, e)
            raise


class KomodoActionButton(CoordinatorEntity[KomodoCoordinator], ButtonEntity):
    """Button entity to run a custom action command."""

    _attr_entity_registry_enabled_default = False
    _attr_icon = "mdi:script-text-play"

    def __init__(
        self,
        coordinator: KomodoCoordinator,
        api: KomodoClient,
        item_id: str,
        action_id: str,
        action_name: str,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the action button entity."""
        super().__init__(coordinator)
        self._api = api
        self._action_id = action_id
        self._action_name = action_name
        self._attr_unique_id = f"{item_id}_run_button"
        self._attr_device_info = device_info
        self._attr_name = f"Run {action_name} action"

    async def async_press(self) -> None:
        """Trigger the action."""
        _LOGGER.info("Starting action %s", self._action_name)
        try:
            update = await self._api.execute.runAction(
                RunAction(action=self._action_id)
            )
            update = await wait_for_completion(
                self._api, update, f"Action {self._action_name}"
            )
            _LOGGER.info("Completed action %s", self._action_name)
            await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error("Failed to run action %s: %s", self._action_name, e)
            raise


class KomodoStackDeployButton(CoordinatorEntity[KomodoCoordinator], ButtonEntity):
    """Button entity to deploy a stack."""

    def __init__(
        self,
        coordinator: KomodoCoordinator,
        api: KomodoClient,
        item_id: str,
        stack_id: str,
        stack_name: str,
        device_info,
    ) -> None:
        """Initialize the button entity."""
        super().__init__(coordinator)
        self._api = api
        self._stack_id = stack_id
        self._stack_name = stack_name

        self._attr_unique_id = f"{item_id}_deploy_button"
        self._attr_device_info = device_info
        self._attr_name = f"Deploy {stack_name} stack"
        self._attr_icon = "mdi:rocket-launch"

    async def async_press(self) -> None:
        """Deploy the stack."""
        _LOGGER.info("Deploying stack %s", self._stack_name)
        try:
            update = await self._api.execute.deployStack(
                DeployStack(stack=self._stack_id)
            )
            update = await wait_for_completion(
                self._api,
                update,
                f"Deploy stack {self._stack_name}",
            )
            _LOGGER.info("Completed deployment of stack %s", self._stack_name)
            await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error("Failed to deploy stack %s: %s", self._stack_name, e)
            raise


def create_deploy_buttons_for_stacks(
    coordinator: KomodoCoordinator,
    api: KomodoClient,
    entry_id: str,
) -> list[KomodoStackDeployButton]:
    """Create deploy button for each stack."""
    entities: list[KomodoStackDeployButton] = []

    for stack in coordinator.data.stacks.values():
        device_info = create_stack_device_info(
            stack, coordinator.server_device_ids, base_url=coordinator.host_url
        )

        entity = KomodoStackDeployButton(
            coordinator=coordinator,
            api=api,
            item_id=f"{entry_id}_{stack.id}",
            stack_id=stack.id,
            stack_name=stack.name,
            device_info=device_info,
        )
        entities.append(entity)

    return entities


class KomodoBuildRunButton(CoordinatorEntity[KomodoCoordinator], ButtonEntity):
    """Button entity to trigger a build pipeline."""

    _attr_entity_registry_enabled_default = False
    _attr_icon = "mdi:hammer-wrench"

    def __init__(
        self,
        coordinator: KomodoCoordinator,
        api: KomodoClient,
        item_id: str,
        build_id: str,
        build_name: str,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the build button entity."""
        super().__init__(coordinator)
        self._api = api
        self._build_id = build_id
        self._build_name = build_name
        self._attr_unique_id = f"{item_id}_run_button"
        self._attr_device_info = device_info
        self._attr_name = f"Run {build_name} build"

    async def async_press(self) -> None:
        """Trigger the build."""
        _LOGGER.info("Starting build %s", self._build_name)
        try:
            update = await self._api.execute.runBuild(
                RunBuild(build=self._build_id)
            )
            update = await wait_for_completion(
                self._api,
                update,
                f"Run build {self._build_name}",
            )
            _LOGGER.info("Completed build %s", self._build_name)
            await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error("Failed to run build %s: %s", self._build_name, e)
            raise


def create_build_buttons(
    coordinator: KomodoCoordinator,
    api: KomodoClient,
    entry_id: str,
) -> list[KomodoBuildRunButton]:
    """Create run build button for each build pipeline."""
    entities: list[KomodoBuildRunButton] = []
    if not coordinator.data or not coordinator.data.builds:
        return entities

    for build in coordinator.data.builds.values():
        device_info = create_build_device_info(build, base_url=coordinator.host_url)
        entity = KomodoBuildRunButton(
            coordinator=coordinator,
            api=api,
            item_id=f"{entry_id}_{build.id}",
            build_id=build.id,
            build_name=build.name,
            device_info=device_info,
        )
        entities.append(entity)

    return entities


def create_procedure_buttons(
    coordinator: KomodoCoordinator,
    api: KomodoClient,
    entry_id: str,
) -> list[KomodoProcedureButton]:
    """Create run procedure button for each procedure."""
    entities: list[KomodoProcedureButton] = []
    if not coordinator.data or not coordinator.data.procedures:
        return entities

    for procedure in coordinator.data.procedures.values():
        device_info = create_procedure_device_info(
            procedure, base_url=coordinator.host_url
        )
        entity = KomodoProcedureButton(
            coordinator=coordinator,
            api=api,
            item_id=f"{entry_id}_{procedure.id}",
            procedure_id=procedure.id,
            procedure_name=procedure.name,
            device_info=device_info,
        )
        entities.append(entity)

    return entities


def create_action_buttons(
    coordinator: KomodoCoordinator,
    api: KomodoClient,
    entry_id: str,
) -> list[KomodoActionButton]:
    """Create run action button for each action."""
    entities: list[KomodoActionButton] = []
    if not coordinator.data or not coordinator.data.actions:
        return entities

    for action in coordinator.data.actions.values():
        device_info = create_action_device_info(action, base_url=coordinator.host_url)
        entity = KomodoActionButton(
            coordinator=coordinator,
            api=api,
            item_id=f"{entry_id}_{action.id}",
            action_id=action.id,
            action_name=action.name,
            device_info=device_info,
        )
        entities.append(entity)

    return entities
