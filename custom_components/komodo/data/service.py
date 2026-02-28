from komodo_api.types import (
    StackService,
    InspectStackContainerResponse,
    ContainerStateStatusEnum,
)

class KomodoUpdateInfo:
    """Update information for a service."""
    current_version: str
    new_version: str
    info_updated_at: float

    def __init__(self, info: InspectStackContainerResponse):
        self.info = info

class KomodoService:
    """Wrapper for a stack service (container)."""

    name: str
    update_available: bool
    state: ContainerStateStatusEnum | None
    update_info: KomodoUpdateInfo | None

    def __init__(self, item: StackService, update_info: KomodoUpdateInfo | None = None):
        self.name = item.service
        self.update_available = item.update_available
        self.state = item.container.state if item.container else None
        if item.update_available:
            self.update_info = update_info
        else:
            self.update_info = None

    def apply_update_info(
        self,
        update_info: KomodoUpdateInfo,
    ) -> None:
        """Apply new update info."""
        self.update_info = update_info
