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

    def add_service(self, service: "KomodoService") -> None:
        """Store a service for this stack."""
        self.services[service.name] = service

    def add_alert(self, alert) -> None:
        """Add an alert to this stack."""
        self.alerts.append(alert.id)

    @classmethod
    def unknown(cls) -> "KomodoStack":
        """Create unknown stack."""
        self = cls.__new__(cls)
        self.state = None
        self.id = "unknown"
        self.name = "unknown"
        self.server_id = "unknown"
        self.services = {}
        self.alerts = []
        return self
