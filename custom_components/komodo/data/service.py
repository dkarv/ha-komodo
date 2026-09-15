from komodo_api.types import (
    StackServiceWithUpdate,
    InspectStackContainerResponse,
    ContainerStateStatusEnum,
)
from releaseprobe import UpdateCheck
from releaseprobe.changelog import ReleaseNote


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

    def __init__(self, info: InspectStackContainerResponse, updated_at: float):
        if info.config and info.config.labels:
            self.current_version = info.config.labels.get(
                "org.opencontainers.image.version", "0"
            )
        else:
            self.current_version = "0"
        self.new_version = "update available"
        self.info_updated_at = updated_at
        self.release_summary = None
        self.release_url = None
        self.release_notes = None

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
    update_available: bool
    state: ContainerStateStatusEnum | None
    update_info: KomodoUpdateInfo | None

    def __init__(self, item: StackServiceWithUpdate, update_info: KomodoUpdateInfo | None = None):
        self.name = item.service
        self.update_available = item.update_available
        self.state = None
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
