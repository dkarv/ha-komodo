"""Update entities for Komodo."""

from __future__ import annotations

from typing import Any
import logging

from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import DOMAIN
from .base import KomodoBase
from komodo_api.types import StackListItem, StackServiceWithUpdate, InspectStackContainerResponse
from .coordinator import KomodoCoordinator
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Setup update platform."""
    komodo: KomodoBase = hass.data[DOMAIN][entry.entry_id]

    await komodo.first_refresh()
    # FIXME catch invalid auth exception and raise ConfigEntryAuthFailed

    stacks: list[StackListItem] = komodo.coordinator.data.stacks.values()
    seen = set()
    async_add_entities(
        KomodoUpdateEntity(komodo.coordinator, entry.entry_id, stack.name, service.service)
        for stack in stacks for service in stack.info.services
        if not ((stack.name, service.service) in seen or seen.add((stack.name, service.service)))
    )

class KomodoUpdateEntity(CoordinatorEntity[KomodoCoordinator], UpdateEntity):

    _attr_supported_features = (
        UpdateEntityFeature.INSTALL | UpdateEntityFeature.RELEASE_NOTES
    )
    _stack: str
    _service: str

    def __init__(
        self,
        coordinator: KomodoCoordinator,
        id: str,
        stack: str,
        service: str,
    ) -> None:
        """Initialize the update entity."""
        super().__init__(coordinator)
        self._stack = stack
        self._service = service
        entity_id = f"update_{stack}_{service}"
        self.entity_id = f"update.{DOMAIN}_{entity_id}"
        self._attr_unique_id = f"{id}_{entity_id}"
    
    def _find_service(self) -> StackServiceWithUpdate | None:
        """Find the service in the coordinator data."""
        stack = self.coordinator.data.stacks.get(self._stack)
        if not stack:
            return None
        return next((s for s in stack.info.services if s.service == self._service), None)
    
    def _find_version(self) -> InspectStackContainerResponse | None:
        """Find the version details for the service."""
        return self.coordinator.data.services.get((self._stack, self._service))

    
    @property
    def name(self) -> str | None:
        """Return the name."""
        return f"{self._stack} - {self._service} update"

    @property
    def latest_version(self) -> str:
        """Return latest version of the entity."""
        service = self._find_service()
        if service and service.update_available:
            return "update"
        return "0"

#    @property
#    def release_url(self) -> str:
#        """Return the URL of the release page."""
#        if self.repository.display_version_or_commit == "commit":
#            return f"https://github.com/{self.repository.data.full_name}"
#        return f"https://github.com/{self.repository.data.full_name}/releases/{self.latest_version}"

    @property
    def installed_version(self) -> str:
        """Return downloaded version of the entity."""
        details = self._find_version()
        if details and details.config and details.config.labels:
            return details.config.labels.get("org.opencontainers.image.version")
        return "0"

    async def async_install(self, version: str | None, backup: bool, **kwargs: Any) -> None:
        """Install an update."""
        # FIXME

    async def async_release_notes(self) -> str | None:
        """Return the release notes."""
        return "Release notes"
        # FIXME
