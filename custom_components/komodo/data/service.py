from komodo_api.types import (
    StackServiceWithUpdate,
    ContainerListItem,
    ContainerStateStatusEnum,
    ContainerStats,
)
from releaseprobe import UpdateCheck
from releaseprobe.changelog import ReleaseNote

from ..utils import parse_docker_percent, parse_docker_size, split_docker_pair


def _format_release_notes(notes: list[ReleaseNote]) -> str:
    """Render pending release notes as markdown, newest first."""
    sections = []
    for note in reversed(notes):
        header = f"## {note.name or note.version}"
        if note.url:
            header += f"\n{note.url}"
        sections.append(f"{header}\n\n{note.body or ''}".strip())
    return "\n\n---\n\n".join(sections)


class KomodoUpdateInfo:
    """Update information for a service."""

    current_version: str
    new_version: str
    info_updated_at: float
    release_summary: str | None
    release_url: str | None
    release_notes: str | None

    def __init__(self, updated_at: float):
        self.current_version = "0"
        self.new_version = "update available"
        self.info_updated_at = updated_at
        self.release_summary = None
        self.release_url = None
        self.release_notes = None

    def apply_labels(self, labels: dict[str, str]) -> None:
        """Take the current version from the container's labels."""
        self.current_version = labels.get("org.opencontainers.image.version", "0")

    def apply_release_info(self, check: UpdateCheck) -> None:
        """Apply the result of a releaseprobe update check."""
        if check.latest_version:
            self.new_version = check.latest_version
        if check.release_notes:
            latest_note = check.release_notes[-1]
            self.release_summary = latest_note.name or latest_note.version
            self.release_notes = _format_release_notes(check.release_notes)
            # Prefer the specific release page over the generic repo URL.
            self.release_url = latest_note.url
        if self.release_url is None and check.latest_info:
            self.release_url = check.latest_info.release_notes_url()


class KomodoService:
    """Wrapper for a stack service (container)."""

    name: str
    image: str
    update_available: bool
    state: ContainerStateStatusEnum | None
    container_id: str | None
    stats: ContainerStats | None
    update_info: KomodoUpdateInfo | None

    def __init__(self, item: StackServiceWithUpdate, update_info: KomodoUpdateInfo | None = None):
        self.name = item.service
        self.image = item.image
        self.update_available = item.update_available
        self.state = None
        self.container_id = None
        self.stats = None
        if item.update_available:
            self.update_info = update_info
        else:
            self.update_info = None

    @property
    def has_container(self) -> bool:
        """True when Komodo reported a container for this service."""
        return self.state is not None

    def apply_container(self, container: ContainerListItem) -> None:
        """Apply the container summary from ListAllStackServices.

        Note: Komodo core never sends `labels` in container list items (too
        big, skip_serializing on the Rust side), so those have to come from
        inspectStackContainer - see KomodoCoordinator._fetch_container_labels.
        """
        self.state = container.state
        self.container_id = container.id
        self.stats = container.stats
        if container.image:
            self.image = container.image

    def _stats_pair(self, field: str) -> tuple[float | None, float | None]:
        """Parse a 'a / b' docker stats field into two byte values."""
        if self.stats is None:
            return None, None
        first, second = split_docker_pair(getattr(self.stats, field))
        return parse_docker_size(first), parse_docker_size(second)

    @property
    def cpu_percent(self) -> float | None:
        """CPU usage of the container in percent (can exceed 100 on multi-core)."""
        if self.stats is None:
            return None
        return parse_docker_percent(self.stats.cpu_perc)

    @property
    def memory_used_bytes(self) -> float | None:
        """Memory used by the container, in bytes."""
        return self._stats_pair("mem_usage")[0]

    @property
    def network_rx_bytes(self) -> float | None:
        """Network bytes received by the container."""
        return self._stats_pair("net_io")[0]

    @property
    def network_tx_bytes(self) -> float | None:
        """Network bytes sent by the container."""
        return self._stats_pair("net_io")[1]

    @property
    def block_read_bytes(self) -> float | None:
        """Bytes read from block devices by the container."""
        return self._stats_pair("block_io")[0]

    @property
    def block_write_bytes(self) -> float | None:
        """Bytes written to block devices by the container."""
        return self._stats_pair("block_io")[1]

    def apply_update_info(
        self,
        update_info: KomodoUpdateInfo,
    ) -> None:
        """Apply new update info."""
        self.update_info = update_info
