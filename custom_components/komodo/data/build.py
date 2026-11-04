from komodo_api.types import (
    ResourceListItem,
    BuildListItemInfo,
    BuildState,
)


class KomodoBuild:
    """Wrapper for a build pipeline item returned from the API."""

    id: str
    name: str
    state: BuildState | str | None
    version: str | None
    last_built_at: str | None
    built_hash: str | None
    latest_hash: str | None
    repo: str | None
    branch: str | None
    repo_link: str | None
    builder_id: str | None

    def __init__(self, item: ResourceListItem[BuildListItemInfo]) -> None:
        self.id = item.id
        self.name = item.name
        self.state = getattr(item.info, "state", None)
        self.version = getattr(item.info, "version", None)
        self.last_built_at = getattr(item.info, "last_built_at", None)
        self.built_hash = getattr(item.info, "built_hash", None)
        self.latest_hash = getattr(item.info, "latest_hash", None)
        self.repo = getattr(item.info, "repo", None)
        self.branch = getattr(item.info, "branch", None)
        self.repo_link = getattr(item.info, "repo_link", None)
        self.builder_id = getattr(item.info, "builder_id", None)
