from komodo_api.types import (
    ResourceListItem,
    ActionListItemInfo,
    ActionState,
)


class KomodoAction:
    """Wrapper for an action item returned from the API."""

    id: str
    name: str
    state: ActionState | str | None
    last_run_at: str | None
    next_scheduled_run: str | None
    schedule_error: str | None

    def __init__(self, item: ResourceListItem[ActionListItemInfo]) -> None:
        self.id = item.id
        self.name = item.name
        self.state = getattr(item.info, "state", None)
        self.last_run_at = getattr(item.info, "last_run_at", None)
        self.next_scheduled_run = getattr(item.info, "next_scheduled_run", None)
        self.schedule_error = getattr(item.info, "schedule_error", None)
