from komodo_api.types import (
    ServerListItem,
    ServerState,
    ResourceListItem,
)
from typing import List


class KomodoServer:
    """Wrapper for a server list item returned from the API."""

    state: ServerState | None
    id: str
    name: str
    alerts: List[str]
    stack_count: int
    service_count: int
    periphery_version: str | None

    def __init__(self, item: ResourceListItem[ServerListItem]):
        self.state = item.info.state
        self.id = item.id
        self.name = item.name
        self.alerts = []
        self.stack_count = 0
        self.service_count = 0
        self.periphery_version = item.info.version

    def add_alert(self, alert) -> None:
        """Add an alert to this server."""
        self.alerts.append(alert.data.type)

    def add_stack(self) -> None:
        """Increment stack count for this server."""
        self.stack_count += 1

    def add_services(self, count: int) -> None:
        """Add services to this server."""
        self.service_count += count

    @classmethod
    def unknown(cls, server_id: str) -> "KomodoServer":
        """Create unknown server."""
        self = cls.__new__(cls)
        self.id = server_id
        self.name = f"Unknown Server {server_id}"
        self.state = None
        self.alerts = []
        self.stack_count = 0
        self.service_count = 0
        self.periphery_version = None
        return self
