from komodo_api.types import (
    ResourceListItem,
    ProcedureListItemInfo,
    ProcedureState,
)


class KomodoProcedure:
    """Wrapper for a procedure item returned from the API."""

    id: str
    name: str
    state: ProcedureState | str | None
    last_run_at: str | None
    next_scheduled_run: str | None
    schedule_error: str | None
    stages: int

    def __init__(self, item: ResourceListItem[ProcedureListItemInfo]) -> None:
        self.id = item.id
        self.name = item.name
        self.state = getattr(item.info, "state", None)
        self.last_run_at = getattr(item.info, "last_run_at", None)
        self.next_scheduled_run = getattr(item.info, "next_scheduled_run", None)
        self.schedule_error = getattr(item.info, "schedule_error", None)
        stages = getattr(item.info, "stages", 0)
        self.stages = len(stages) if isinstance(stages, list) else int(stages or 0)
