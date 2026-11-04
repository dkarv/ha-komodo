from komodo_api.types import (
    ResourceListItem,
    StackListItem,
    StackState,
)
from typing import List

from .service import KomodoService


class KomodoStack:
    """Wrapper for a stack list item returned from the API."""

    state: StackState | None
    id: str
    name: str
    server_id: str | None
    branch: str | None
    deployed_hash: str | None
    latest_hash: str | None
    services: dict[str, KomodoService]
    alerts: List[str]

    def __init__(self, item: ResourceListItem[StackListItem]):
        self.state = item.info.state
        self.id = item.id
        self.name = item.name
        # Komodo reports an empty server_id for stacks not assigned to a server.
        self.server_id = item.info.server_id or None
        self.branch = getattr(item.info, "branch", None)
        self.deployed_hash = getattr(item.info, "deployed_hash", None)
        self.latest_hash = getattr(item.info, "latest_hash", None)
        self.services = {}
        self.alerts = []

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
        self.server_id = None
        self.branch = None
        self.deployed_hash = None
        self.latest_hash = None
        self.services = {}
        self.alerts = []
        return self
