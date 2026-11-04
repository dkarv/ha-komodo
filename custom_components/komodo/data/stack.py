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
    server_name: str | None
    repo_link: str | None
    git_provider: str | None
    repo: str | None
    branch: str | None
    services: dict[str, KomodoService]
    alerts: List[str]

    def __init__(self, item: ResourceListItem[StackListItem]):
        self.state = item.info.state
        self.id = item.id
        self.name = item.name
        sid = getattr(item.info, "server_id", None)
        self.server_id = sid if sid else None
        sname = getattr(item.info, "server_name", None)
        self.server_name = sname if sname else None
        self.repo_link = getattr(item.info, "repo_link", None)
        self.git_provider = getattr(item.info, "git_provider", None)
        self.repo = getattr(item.info, "repo", None)
        self.branch = getattr(item.info, "branch", None)
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
        self.server_name = None
        self.repo_link = None
        self.git_provider = None
        self.repo = None
        self.branch = None
        self.services = {}
        self.alerts = []
        return self
