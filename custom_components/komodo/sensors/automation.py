from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from komodo_api.types import ActionState, ProcedureState

from ..coordinator import KomodoCoordinator
from ..data.komodo_data import KomodoData
from ..utils import create_komodo_main_device_info
from .common import KomodoOptionSensor, KomodoSensor


class KomodoProcedureStateSensor(KomodoOptionSensor):
    """Sensor for procedure state with runbook execution details."""

    def __init__(
        self,
        coordinator: KomodoCoordinator,
        item_id: str,
        procedure_id: str,
        device_info: DeviceInfo,
    ) -> None:
        self._procedure_id = procedure_id
        super().__init__(
            item_id=item_id,
            coordinator=coordinator,
            extractor=self._extract_state,
            key="procedure_state",
            device_info=device_info,
            options=[state.name for state in ProcedureState],
            enabled_default=False,
        )

    def _extract_state(self, data: KomodoData) -> str:
        proc = data.procedures.get(self._procedure_id)
        if not proc or not proc.state:
            return ProcedureState.UNKNOWN.name
        if hasattr(proc.state, "name"):
            return proc.state.name
        return str(proc.state).upper()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return runbook stages and scheduling attributes."""
        if not self.coordinator.data or not self.coordinator.data.procedures:
            return {}
        proc = self.coordinator.data.procedures.get(self._procedure_id)
        if not proc:
            return {}
        return {
            "stages": proc.stages,
            "last_run_at": proc.last_run_at,
            "next_scheduled_run": proc.next_scheduled_run,
            "schedule_error": proc.schedule_error,
        }


class KomodoActionStateSensor(KomodoOptionSensor):
    """Sensor for action command execution state."""

    def __init__(
        self,
        coordinator: KomodoCoordinator,
        item_id: str,
        action_id: str,
        device_info: DeviceInfo,
    ) -> None:
        self._action_id = action_id
        super().__init__(
            item_id=item_id,
            coordinator=coordinator,
            extractor=self._extract_state,
            key="action_state",
            device_info=device_info,
            options=[state.name for state in ActionState],
            enabled_default=False,
        )

    def _extract_state(self, data: KomodoData) -> str:
        act = data.actions.get(self._action_id)
        if not act or not act.state:
            return ActionState.UNKNOWN.name
        if hasattr(act.state, "name"):
            return act.state.name
        return str(act.state).upper()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return scheduling and last run attributes."""
        if not self.coordinator.data or not self.coordinator.data.actions:
            return {}
        act = self.coordinator.data.actions.get(self._action_id)
        if not act:
            return {}
        return {
            "last_run_at": act.last_run_at,
            "next_scheduled_run": act.next_scheduled_run,
            "schedule_error": act.schedule_error,
        }


def create_automation_sensors(
    coordinator: KomodoCoordinator,
    entry_id: str,
) -> list[KomodoSensor]:
    """Create sensors for Komodo procedures and actions."""
    sensors: list[KomodoSensor] = []
    if not coordinator.data:
        return sensors

    device_info = create_komodo_main_device_info(entry_id, coordinator)

    for proc in coordinator.data.procedures.values():
        item_id = f"{entry_id}_procedure_{proc.id}"
        sensors.append(
            KomodoProcedureStateSensor(
                coordinator=coordinator,
                item_id=item_id,
                procedure_id=proc.id,
                device_info=device_info,
            )
        )

    for act in coordinator.data.actions.values():
        item_id = f"{entry_id}_action_{act.id}"
        sensors.append(
            KomodoActionStateSensor(
                coordinator=coordinator,
                item_id=item_id,
                action_id=act.id,
                device_info=device_info,
            )
        )

    return sensors
