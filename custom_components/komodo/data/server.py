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

    def __init__(self, item: ResourceListItem[ServerListItem]):
        self.state = item.info.state
        self.id = item.id
        self.name = item.name
        self.alerts = []

    def add_alert(self, alert) -> None:
        """Add an alert to this server."""
        self.alerts.append(alert.id)

    @classmethod
    def unknown(cls) -> "KomodoServer":
        """Create unknown server."""
        self = cls.__new__(cls)
        self.state = None
        self.alerts = []
        return self
