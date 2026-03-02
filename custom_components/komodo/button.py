from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from komodo_api.types import (
    ListProcedures,
    ListProceduresResponse,
    ResourceListItem,
    ProcedureListItemInfo,
    RunProcedure,
    DeployStack,
)
from komodo_api.lib import KomodoClient

from custom_components.komodo.base import KomodoBase
from custom_components.komodo.const import DOMAIN
from custom_components.komodo.coordinator import KomodoCoordinator
from custom_components.komodo.utils import wait_for_completion, create_stack_device_info

import logging

_LOGGER = logging.getLogger(__name__)

import logging

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    komodo: KomodoBase = hass.data[DOMAIN][entry.entry_id]

    # Procedure buttons
    try:
        procedures: ListProceduresResponse = await komodo.api.read.listProcedures(
            ListProcedures()
        )
        procedure_entities = [
            KomodoProcedureButton(komodo.api, entry.entry_id, procedure)
            for procedure in procedures
        ]
    except Exception:
        procedure_entities = []

    # Wait for first refresh to get stack data
    await komodo.first_refresh()
    
    # Stack deploy buttons
    deploy_entities = create_deploy_buttons_for_stacks(
        komodo.coordinator, komodo.api, entry.entry_id
    )

    async_add_entities(procedure_entities + deploy_entities)



class KomodoProcedureButton(ButtonEntity):
    def __init__(
        self,
        api: KomodoClient,
        id: str,
        procedure: ResourceListItem[ProcedureListItemInfo],
    ):
        self._api = api
        self._procedure = procedure
        entity_id = f"button_{procedure.id}"
        self.entity_id = f"button.{DOMAIN}_{entity_id}"
        self._attr_unique_id = f"{id}_{entity_id}"
        self._attr_name = f"Procedure {procedure.name}"

    async def async_press(self) -> None:
        _LOGGER.info("Starting procedure %s", self._procedure.name)
        update = await self._api.execute.runProcedure(
            RunProcedure(procedure=self._procedure.id)
        )
        update = await wait_for_completion(
            self._api, update, f"Procedure {self._procedure.name}"
        )
        _LOGGER.info("Completed procedure %s", self._procedure.name)


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
            stack.id, stack.name, stack.server_id
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
