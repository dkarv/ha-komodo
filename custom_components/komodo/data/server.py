from typing import Optional
from komodo_api.types import (
    ServerListItem,
    ServerState,
    ResourceListItem,
    MinimalSystemStats,
)


class KomodoServer:
    """Wrapper for a server list item returned from the API."""

    state: ServerState | None
    id: str
    name: str
    alerts: list[str]
    stack_count: int
    service_count: int
    periphery_version: str | None
    cpu_percent: Optional[float]
    memory_used_gb: Optional[float]
    memory_total_gb: Optional[float]
    disk_used_gb: Optional[float]
    disk_total_gb: Optional[float]
    load_average_1m: Optional[float]

    def __init__(self, item: ResourceListItem[ServerListItem]):
        self.state = item.info.state
        self.id = item.id
        self.name = item.name
        self.alerts = []
        self.stack_count = 0
        self.service_count = 0
        self.periphery_version = item.info.version
        self._reset_stats()
        if item.info.stats:
            self.set_stats(item.info.stats)

    def _reset_stats(self) -> None:
        self.cpu_percent = None
        self.memory_used_gb = None
        self.memory_total_gb = None
        self.disk_used_gb = None
        self.disk_total_gb = None
        self.load_average_1m = None

    def add_alert(self, alert) -> None:
        """Add an alert to this server."""
        self.alerts.append(alert.data.type)

    def add_stack(self) -> None:
        """Increment stack count for this server."""
        self.stack_count += 1

    def add_services(self, count: int) -> None:
        """Add services to this server."""
        self.service_count += count

    def set_stats(self, stats: MinimalSystemStats) -> None:
        """Update this server with the stats Komodo core caches per server."""
        self.cpu_percent = stats.cpu_perc
        self.memory_used_gb = stats.mem_used_gb
        self.memory_total_gb = stats.mem_total_gb
        self.disk_used_gb = stats.disk_used_gb
        self.disk_total_gb = stats.disk_total_gb
        if stats.load_average:
            self.load_average_1m = stats.load_average.one

    @property
    def memory_percent(self) -> Optional[float]:
        """Return the memory usage percentage, matching the Komodo UI (used/total)."""
        if not self.memory_total_gb or self.memory_used_gb is None:
            return None
        return self.memory_used_gb / self.memory_total_gb * 100

    @property
    def memory_available_gb(self) -> Optional[float]:
        """Return the memory available for new processes (total - used).

        This is the complement of memory_percent, i.e. it includes
        reclaimable disk cache/buffers, unlike the raw kernel 'free' value.
        """
        if self.memory_total_gb is None or self.memory_used_gb is None:
            return None
        return self.memory_total_gb - self.memory_used_gb

    @property
    def disk_percent(self) -> Optional[float]:
        """Return the disk usage percentage."""
        if not self.disk_total_gb:
            return None
        return self.disk_used_gb / self.disk_total_gb * 100

    @property
    def disk_free_gb(self) -> Optional[float]:
        """Return the free disk space in GB."""
        if self.disk_total_gb is None or self.disk_used_gb is None:
            return None
        return self.disk_total_gb - self.disk_used_gb

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
        self._reset_stats()
        return self
