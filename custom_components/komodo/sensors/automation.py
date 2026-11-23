from enum import Enum

from ..coordinator import KomodoCoordinator
from ..data.automation import KomodoAutomation
from ..data.komodo_data import KomodoData
from ..utils import create_action_device_info, create_procedure_device_info
from .common import KomodoOptionSensor, KomodoSensor

from komodo_api.types import ActionState, ProcedureState


def _attributes(item: KomodoAutomation) -> dict:
    """Return scheduling attributes shared by procedures and actions."""
    attrs = {
        "last_run_at": item.last_run_at.isoformat() if item.last_run_at else None,
        "next_scheduled_run": (
            item.next_scheduled_run.isoformat() if item.next_scheduled_run else None
        ),
        "schedule_error": item.schedule_error,
    }
    if (stages := getattr(item, "stages", None)) is not None:
        attrs["stages"] = stages
    return attrs


def _state_sensors(
    coordinator: KomodoCoordinator,
    entry_id: str,
    collection: str,
    key: str,
    states: type[Enum],
    device_info_fn,
) -> list[KomodoSensor]:
    """Create a disabled-by-default state sensor for each item of a collection."""
    sensors: list[KomodoSensor] = []
    for item in getattr(coordinator.data, collection).values():

        def state(data: KomodoData, iid=item.id) -> str:
            found = getattr(data, collection).get(iid)
            return found.state.name if found else states.UNKNOWN.name

        def attributes(data: KomodoData, iid=item.id) -> dict | None:
            found = getattr(data, collection).get(iid)
            return _attributes(found) if found else None

        sensors.append(
            KomodoOptionSensor(
                coordinator=coordinator,
                item_id=f"{entry_id}_{item.id}",
                extractor=state,
                key=key,
                device_info=device_info_fn(item, base_url=coordinator.host_url),
                options=[s.name for s in states],
                enabled_default=False,
                attributes_extractor=attributes,
            )
        )
    return sensors


def create_automation_sensors(
    coordinator: KomodoCoordinator,
    entry_id: str,
) -> list[KomodoSensor]:
    """Create state sensors for Komodo procedures and actions."""
    return _state_sensors(
        coordinator,
        entry_id,
        "procedures",
        "procedure_state",
        ProcedureState,
        create_procedure_device_info,
    ) + _state_sensors(
        coordinator,
        entry_id,
        "actions",
        "action_state",
        ActionState,
        create_action_device_info,
    )
