from typing import Any

from komodo_api.types import (
    StackServiceWithUpdate,
    ContainerListItem,
    ContainerStateStatusEnum,
    ContainerStats,
)
from releaseprobe import UpdateCheck
from releaseprobe.changelog import ReleaseNote

from ..utils import (
    parse_docker_percent,
    parse_docker_size,
    split_docker_pair,
    clean_image_name,
    extract_version_from_labels,
    extract_version_from_env,
    extract_version_from_image_tag,
)


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

    def __init__(self, updated_at: float, current_version: str = "0", new_version: str = "update available"):
        self.current_version = current_version
        self.new_version = new_version
        self.info_updated_at = updated_at
        self.release_summary = None
        self.release_url = None
        self.release_notes = None

    def apply_labels(self, labels: dict[str, str]) -> None:
        """Extract the current version from the container's labels."""
        version = extract_version_from_labels(labels)
        self.current_version = version or "0"

    def apply_env(self, env: list[str], service_name: str | None = None) -> None:
        """Extract the current version from container environment variables."""
        version = extract_version_from_env(env, service_name=service_name)
        if version and (self.current_version in ("0", "unknown") or not self.current_version):
            self.current_version = version

    def apply_release_info(self, check: UpdateCheck) -> None:
        """Apply the result of a releaseprobe update check."""
        if check.current_version and (self.current_version in ("0", "unknown") or not self.current_version):
            self.current_version = check.current_version
        elif check.current_info and check.current_info.version and (self.current_version in ("0", "unknown") or not self.current_version):
            self.current_version = check.current_info.version

        if check.latest_version:
            self.new_version = check.latest_version
        elif check.latest_info and check.latest_info.version:
            self.new_version = check.latest_info.version

        if check.release_notes:
            latest_note = check.release_notes[-1]
            self.release_summary = latest_note.name or latest_note.version
            self.release_notes = _format_release_notes(check.release_notes)
            # Prefer the specific release page over the generic repo URL.
            self.release_url = latest_note.url
        if self.release_url is None and check.latest_info:
            self.release_url = check.latest_info.release_notes_url()

    def apply_registry_labels(self, labels: dict[str, str]) -> None:
        """Extract the latest version from fetched registry labels for floating tags."""
        version = extract_version_from_labels(labels)
        if version and self.new_version in ("update available", "0", None):
            self.new_version = version
        if not self.release_url:
            url = labels.get("org.opencontainers.image.url") or labels.get("org.opencontainers.image.source")
            if url:
                self.release_url = url


class KomodoService:
    """Wrapper for a stack service (container)."""

    name: str
    image: str
    latest_image: str | None
    config_image: str | None
    image_digests: list[str]
    update_available: bool
    state: ContainerStateStatusEnum | None
    container_id: str | None
    stats: ContainerStats | None
    update_info: KomodoUpdateInfo | None
    labels: dict[str, str]
    env: list[str]

    def __init__(self, item: StackServiceWithUpdate, update_info: KomodoUpdateInfo | None = None):
        self.name = item.service
        self.image = item.image
        self.latest_image = getattr(item, "latest_image", None)
        self.config_image = None
        self.image_digests = []
        self.update_available = item.update_available
        self.state = None
        self.container_id = None
        self.stats = None
        self.labels = {}
        self.env = []
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
            # Preserve repo name if container only reported an image hash
            if not container.image.startswith("sha256:") or not self.image or self.image.startswith("sha256:"):
                self.image = container.image

    def apply_stack_service(self, item: Any) -> None:
        """Apply stack service information including image digests."""
        if getattr(item, "image_digests", None):
            self.image_digests = list(item.image_digests)
        if getattr(item, "container", None):
            self.apply_container(item.container)

    @property
    def effective_image(self) -> str:
        """Return the best usable image reference for registry queries."""
        if self.config_image and not self.config_image.startswith("sha256:"):
            return clean_image_name(self.config_image)
        if self.latest_image and not self.latest_image.startswith("sha256:"):
            return clean_image_name(self.latest_image)
        if self.image and not self.image.startswith("sha256:"):
            return clean_image_name(self.image)
        for d in self.image_digests:
            if "@sha256:" in d:
                repo = d.split("@sha256:")[0]
                if repo and not repo.startswith("sha256:"):
                    return clean_image_name(repo)
        return self.image or ""

    @property
    def installed_version(self) -> str:
        """Return the resolved installed version of the container."""
        if self.update_info and self.update_info.current_version and self.update_info.current_version != "0":
            return self.update_info.current_version

        if ver := extract_version_from_labels(self.labels):
            return ver

        if ver := extract_version_from_env(self.env, service_name=self.name):
            return ver

        img = self.effective_image or self.image
        if img and (tag := extract_version_from_image_tag(img)):
            return tag

        if self.image and self.image.startswith("sha256:"):
            return self.image[7:15]

        if self.container_id:
            return self.container_id[:8]

        return "0"


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
