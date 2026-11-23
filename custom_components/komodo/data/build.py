from datetime import datetime, timezone

from komodo_api.types import (
    BuildListItemInfo,
    BuildState,
    ResourceListItem,
)


class KomodoBuild:
    """Wrapper for a build list item returned from the API."""

    id: str
    name: str
    state: BuildState
    version: str | None
    last_built_at: datetime | None
    built_hash: str | None
    latest_hash: str | None
    repo: str | None
    branch: str | None
    repo_link: str | None

    def __init__(self, item: ResourceListItem[BuildListItemInfo]) -> None:
        info = item.info
        self.id = item.id
        self.name = item.name
        self.state = info.state
        # Komodo reports 0.0.0 for builds without a version.
        v = info.version
        self.version = (
            f"{v.major}.{v.minor}.{v.patch}" if (v.major, v.minor, v.patch) != (0, 0, 0) else None
        )
        # Unix timestamp in milliseconds, 0 if never built.
        self.last_built_at = (
            datetime.fromtimestamp(info.last_built_at / 1000, tz=timezone.utc)
            if info.last_built_at
            else None
        )
        self.built_hash = info.built_hash
        self.latest_hash = info.latest_hash
        # Komodo reports empty strings for builds without a repo.
        self.repo = info.repo or None
        self.branch = info.branch or None
        self.repo_link = info.repo_link or None
