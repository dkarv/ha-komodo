"""Switch platform for Komodo services."""

from __future__ import annotations
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from komodo_api.types import (
    ContainerStateStatusEnum,
    StartContainer,
    StopContainer,
    InspectStackContainerResponse,
    InspectStackContainer,
    DeployStack,
    StopStack,
    StackState,
)

from .utils import wait_for_completion, create_stack_device_info
from .const import DOMAIN
from .base import KomodoBase
from .coordinator import KomodoCoordinator
from .data.service import KomodoService
from .data.stack import KomodoStack
from komodo_api.lib import KomodoClient

_LOGGER = logging.getLogger(__name__)


class KomodoServiceSwitch(CoordinatorEntity[KomodoCoordinator], SwitchEntity):
    """Switch entity for a service in a stack."""

    def __init__(
        self,
        coordinator: KomodoCoordinator,
        api: KomodoClient,
        item_id: str,
        stack_id: str,
        stack_name: str,
        service_name: str,
        server_id: str,
        device_info,
    ) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator)
        self._api = api
        self._stack_id = stack_id
        self._stack_name = stack_name
        self._service_name = service_name
        self._server_id = server_id

        self._attr_unique_id = f"{item_id}_switch"
        self._attr_device_info = device_info
        self._attr_name = f"{service_name}"
        self._attr_has_entity_name = True

        self._update_attrs()

    def _find_service(self) -> KomodoService | None:
        """Find the service in the coordinator data."""
        stack = self.coordinator.data.stacks.get(self._stack_id)
        if not stack:
            return None
        return stack.services.get(self._service_name)

    def _update_attrs(self) -> None:
        """Update entity attributes from coordinator data."""
        service = self._find_service()
        if service and service.state is not None:
            # Service is "on" when state is RUNNING
            self._attr_is_on = service.state == ContainerStateStatusEnum.RUNNING
        else:
            self._attr_is_on = None
    
    async def query_container(self) -> str:
        """Query the container id."""
        service = self._find_service()
        if service and service.container_id:
            return service.container_id
        response: InspectStackContainerResponse = await self._api.read.inspectStackContainer(InspectStackContainer(stack = self._stack_id, service = self._service_name))
        return response.id

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start the service."""
        _LOGGER.info("Starting service %s in stack %s", self._service_name, self._stack_name)
        try:
            container = await self.query_container()
            update = await self._api.execute.startContainer(StartContainer(server=self._server_id, container = container))
            update = await wait_for_completion(
                self.coordinator.my_api,
                update,
                f"Start {self._stack_name}/{self._service_name}",
            )
            await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error("Failed to start service %s: %s", self._service_name, e)
            raise

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop the service."""
        _LOGGER.info("Stopping service %s in stack %s", self._service_name, self._stack_name)
        try:
            container = await self.query_container()
            update = await self._api.execute.stopContainer(StopContainer(server=self._server_id, container= container))
            update = await wait_for_completion(
                self.coordinator.my_api,
                update,
                f"Stop {self._stack_name}/{self._service_name}",
            )
            await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error("Failed to stop service %s: %s", self._service_name, e)
            raise

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_attrs()
        self.async_write_ha_state()


class KomodoStackSwitch(CoordinatorEntity[KomodoCoordinator], SwitchEntity):
    """Switch entity to deploy or stop a full stack at once."""

    def __init__(
        self,
        coordinator: KomodoCoordinator,
        api: KomodoClient,
        item_id: str,
        stack_id: str,
        stack_name: str,
        device_info,
    ) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator)
        self._api = api
        self._stack_id = stack_id
        self._stack_name = stack_name

        self._attr_unique_id = f"{item_id}_stack_switch"
        self._attr_device_info = device_info
        self._attr_name = "Stack"
        self._attr_has_entity_name = True
        self._attr_icon = "mdi:layers"

        self._update_attrs()

    def _find_stack(self) -> KomodoStack | None:
        """Find the stack in the coordinator data."""
        return self.coordinator.data.stacks.get(self._stack_id)

    def _update_attrs(self) -> None:
        """Update entity attributes from coordinator data."""
        stack = self._find_stack()
        if stack and stack.state is not None:
            self._attr_is_on = stack.state == StackState.RUNNING
        else:
            self._attr_is_on = None

    async def async_turn_on(self, **kwargs: Any) -> None:
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
            await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error("Failed to deploy stack %s: %s", self._stack_name, e)
            raise

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop the stack."""
        _LOGGER.info("Stopping stack %s", self._stack_name)
        try:
            update = await self._api.execute.stopStack(
                StopStack(stack=self._stack_id)
            )
            update = await wait_for_completion(
                self._api,
                update,
                f"Stop stack {self._stack_name}",
            )
            await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error("Failed to stop stack %s: %s", self._stack_name, e)
            raise

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_attrs()
        self.async_write_ha_state()


def create_switch_entities_for_stacks(
    api: KomodoClient,
    coordinator: KomodoCoordinator,
    entry_id: str,
) -> list[KomodoStackSwitch]:
    """Create a deploy/stop switch for each stack."""
    entities: list[KomodoStackSwitch] = []

    for stack in coordinator.data.stacks.values():
        device_info = create_stack_device_info(
            stack.id, stack.name, stack.server_id
        )

        entity = KomodoStackSwitch(
            coordinator=coordinator,
            api=api,
            item_id=f"{entry_id}_{stack.id}",
            stack_id=stack.id,
            stack_name=stack.name,
            device_info=device_info,
        )
        entities.append(entity)

    return entities


def create_switch_entities_for_services(
    api: KomodoClient,
    coordinator: KomodoCoordinator,
    entry_id: str,
) -> list[KomodoServiceSwitch]:
    """Create switch entities for each service in each stack."""
    entities: list[KomodoServiceSwitch] = []

    for stack in coordinator.data.stacks.values():
        device_info = create_stack_device_info(
            stack.id, stack.name, stack.server_id
        )

        for service in stack.services.values():
            entity = KomodoServiceSwitch(
                coordinator=coordinator,
                api = api,
                item_id=f"{entry_id}_{stack.id}_{service.name}",
                stack_id=stack.id,
                stack_name=stack.name,
                service_name=service.name,
                server_id=stack.server_id,
                device_info=device_info,
            )
            entities.append(entity)

    return entities


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Setup switch platform."""
    komodo: KomodoBase = hass.data[DOMAIN][entry.entry_id]

    stack_switches = create_switch_entities_for_stacks(komodo.api, komodo.coordinator, entry.entry_id)
    service_switches = create_switch_entities_for_services(komodo.api, komodo.coordinator, entry.entry_id)
    async_add_entities(stack_switches + service_switches)
