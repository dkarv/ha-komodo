from datetime import datetime, timezone

from komodo_api.types import (
    ActionListItemInfo,
    ActionState,
    ProcedureListItemInfo,
    ProcedureState,
    ResourceListItem,
)


def _from_ms(ts: int | None) -> datetime | None:
    """Convert a Komodo unix timestamp in milliseconds to a datetime."""
    return datetime.fromtimestamp(ts / 1000, tz=timezone.utc) if ts else None


class KomodoAutomation:
    """Common fields of procedures and actions."""

    id: str
    name: str
    last_run_at: datetime | None
    next_scheduled_run: datetime | None
    schedule_error: str | None

    def __init__(
        self, item: ResourceListItem[ProcedureListItemInfo | ActionListItemInfo]
    ) -> None:
        self.id = item.id
        self.name = item.name
        self.last_run_at = _from_ms(item.info.last_run_at)
        self.next_scheduled_run = _from_ms(item.info.next_scheduled_run)
        self.schedule_error = item.info.schedule_error


class KomodoProcedure(KomodoAutomation):
    """Wrapper for a procedure list item returned from the API."""

    state: ProcedureState
    stages: int

    def __init__(self, item: ResourceListItem[ProcedureListItemInfo]) -> None:
        super().__init__(item)
        self.state = item.info.state
        self.stages = item.info.stages


class KomodoAction(KomodoAutomation):
    """Wrapper for an action list item returned from the API."""

    state: ActionState

    def __init__(self, item: ResourceListItem[ActionListItemInfo]) -> None:
        super().__init__(item)
        self.state = item.info.state
