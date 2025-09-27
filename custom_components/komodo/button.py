from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

from komodo_api.types import ListProcedures, ListProceduresResponse, ResourceListItem, ProcedureListItemInfo, RunProcedure
from komodo_api.lib import KomodoClient

from custom_components.komodo.base import KomodoBase
from custom_components.komodo.const import DOMAIN
from custom_components.komodo.utils import wait_for_completion


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    komodo: KomodoBase = hass.data[DOMAIN][entry.entry_id]

    try:
        procedures: ListProceduresResponse = await komodo.api.read.listProcedures(ListProcedures())
    except Exception as e:
        return

    entities = [
        KomodoProcedureButton(komodo.api, entry.entry_id, procedure)
        for procedure in procedures
    ]
    async_add_entities(entities)

class KomodoProcedureButton(ButtonEntity):
    def __init__(self, 
                 api: KomodoClient, 
                 id: str,
                 procedure: ResourceListItem[ProcedureListItemInfo]):
        self._api = api
        self._procedure = procedure
        entity_id = f"button_{procedure.id}"
        self.entity_id = f"button.{DOMAIN}_{entity_id}"
        self._attr_unique_id = f"{id}_{entity_id}"      
        self._attr_name = f"Procedure {procedure.name}"

    async def async_press(self) -> None:
        update = await self._api.execute.runProcedure(RunProcedure(procedure = self._procedure.id))
        update = await wait_for_completion(self._api, update, f"Procedure {self._procedure.name}")
