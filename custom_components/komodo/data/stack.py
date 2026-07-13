from komodo_api.types import (
    ResourceListItem,
    StackListItem,
    StackState,
)
from typing import List

from .service import KomodoService


# Stack states with no container to inspect: DOWN (stack not deployed) and
# UNKNOWN (server not reachable). Every other state still has a container that
# inspects fine, including STOPPED/CREATED/DEAD/PAUSED.
_NO_CONTAINER_STATES = frozenset({StackState.DOWN, StackState.UNKNOWN})


class KomodoStack:
    """Wrapper for a stack list item returned from the API."""

    state: StackState | None
    id: str
    name: str
    server_id: str
    services: dict[str, KomodoService]
    alerts: List[str]

    def __init__(self, item: ResourceListItem[StackListItem]):
        self.state = item.info.state
        self.id = item.id
        self.name = item.name
        self.server_id = item.info.server_id
        self.services = {}
        self.alerts = []

    @property
    def has_inspectable_container(self) -> bool:
        """False when the stack has no container to inspect."""
        return self.state is not None and self.state not in _NO_CONTAINER_STATES

    def add_service(self, service: "KomodoService") -> None:
        """Store a service for this stack."""
        self.services[service.name] = service

    def add_alert(self, alert) -> None:
        """Add an alert to this stack."""
        self.alerts.append(alert.data.type)

    @classmethod
    def unknown(cls, stack_id: str) -> "KomodoStack":
        """Create unknown stack."""
        self = cls.__new__(cls)
        self.state = None
        self.id = stack_id
        self.name = f"Unknown Stack {stack_id}"
        self.server_id = "unknown"
        self.services = {}
        self.alerts = []
        return self
