"""Update entities for Komodo."""

from __future__ import annotations
import logging
from typing import Any
from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from komodo_api.types import DeployStack, Update

from .utils import wait_for_completion, create_stack_device_info

from .const import DOMAIN
from .base import KomodoBase
from .coordinator import KomodoCoordinator
from .data.service import KomodoService

_LOGGER = logging.getLogger(__name__)


class KomodoUpdateEntity(CoordinatorEntity[KomodoCoordinator], UpdateEntity):
    """Update entity for a service in a stack."""

    _attr_supported_features = UpdateEntityFeature.INSTALL

    def __init__(
        self,
        coordinator: KomodoCoordinator,
        item_id: str,
        stack_id: str,
        stack_name: str,
        service_name: str,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the update entity."""
        super().__init__(coordinator)
        self._stack_id = stack_id
        self._stack_name = stack_name
        self._service_name = service_name

        self._attr_unique_id = f"{item_id}_update"
        self._attr_device_info = device_info
        self._attr_name = service_name

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
        if service and service.update_info:
            self._attr_installed_version = service.update_info.current_version
            self._attr_latest_version = service.update_info.new_version
            self._attr_title = f"{self._service_name}: "
        else:
            self._attr_installed_version = "0"
            self._attr_latest_version = "0"
            self._attr_title = None

    async def async_install(
        self, version: str | None, backup: bool, **kwargs: Any
    ) -> None:
        """Install an update."""
        update: Update = await self.coordinator.my_api.execute.deployStack(
            DeployStack(stack=self._stack_id, services=[self._service_name])
        )
        update = await wait_for_completion(
            self.coordinator.my_api,
            update,
            f"Update of {self._stack_name}/{self._service_name}",
        )
        await self.coordinator.async_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_attrs()
        self.async_write_ha_state()


def create_update_entities_for_services(
    coordinator: KomodoCoordinator,
    entry_id: str,
) -> list[KomodoUpdateEntity]:
    """Create update entities for each service in each stack."""
    entities: list[KomodoUpdateEntity] = []

    for stack in coordinator.data.stacks.values():
        device_info = create_stack_device_info(
            stack.id, stack.name, stack.server_id
        )

        for service in stack.services.values():
            entity = KomodoUpdateEntity(
                coordinator=coordinator,
                item_id=f"{entry_id}_{stack.id}_{service.name}",
                stack_id=stack.id,
                stack_name=stack.name,
                service_name=service.name,
                device_info=device_info,
            )
            entities.append(entity)

    return entities


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Setup update platform."""
    komodo: KomodoBase = hass.data[DOMAIN][entry.entry_id]

    await komodo.first_refresh()

    entities = create_update_entities_for_services(komodo.coordinator, entry.entry_id)
    async_add_entities(entities)
