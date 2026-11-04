from typing import Any
from homeassistant.helpers.device_registry import DeviceInfo
from komodo_api.types import BuildState

from ..coordinator import KomodoCoordinator
from ..data.komodo_data import KomodoData
from ..utils import create_build_device_info
from .common import KomodoOptionSensor, KomodoSensor


class KomodoBuildStateSensor(KomodoOptionSensor):
    """Sensor for build pipeline state with CI/CD attributes."""

    def __init__(
        self,
        coordinator: KomodoCoordinator,
        item_id: str,
        build_id: str,
        device_info: DeviceInfo,
    ) -> None:
        self._build_id = build_id
        super().__init__(
            item_id=item_id,
            coordinator=coordinator,
            extractor=self._extract_state,
            key="build_state",
            device_info=device_info,
            options=[state.name for state in BuildState],
            enabled_default=False,
        )

    def _extract_state(self, data: KomodoData) -> str:
        build = data.builds.get(self._build_id)
        if not build or not build.state:
            return BuildState.UNKNOWN.name
        if hasattr(build.state, "name"):
            return build.state.name
        return str(build.state).upper()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return git commit, branch, and version attributes."""
        if not self.coordinator.data or not self.coordinator.data.builds:
            return {}
        build = self.coordinator.data.builds.get(self._build_id)
        if not build:
            return {}
        return {
            "version": build.version,
            "built_hash": build.built_hash,
            "latest_hash": build.latest_hash,
            "repo": build.repo,
            "branch": build.branch,
            "repo_link": build.repo_link,
            "last_built_at": build.last_built_at,
        }


def create_build_sensors(
    coordinator: KomodoCoordinator,
    entry_id: str,
) -> list[KomodoSensor]:
    """Create sensors for each Komodo build pipeline."""
    sensors: list[KomodoSensor] = []
    if not coordinator.data or not coordinator.data.builds:
        return sensors

    for build in coordinator.data.builds.values():
        device_info = create_build_device_info(build, base_url=coordinator.host_url)
        item_id = f"{entry_id}_build_{build.id}"

        sensors.append(
            KomodoBuildStateSensor(
                coordinator=coordinator,
                item_id=item_id,
                build_id=build.id,
                device_info=device_info,
            )
        )

    return sensors
