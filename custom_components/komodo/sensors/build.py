from komodo_api.types import BuildState

from ..coordinator import KomodoCoordinator
from ..data.komodo_data import KomodoData
from ..utils import create_build_device_info
from .common import KomodoOptionSensor, KomodoSensor


def create_build_sensors(
    coordinator: KomodoCoordinator,
    entry_id: str,
) -> list[KomodoSensor]:
    """Create sensors for each Komodo build (disabled by default)."""
    sensors: list[KomodoSensor] = []
    for build in coordinator.data.builds.values():

        def state(data: KomodoData, bid=build.id) -> str:
            b = data.builds.get(bid)
            return b.state.name if b else BuildState.UNKNOWN.name

        def attributes(data: KomodoData, bid=build.id) -> dict | None:
            b = data.builds.get(bid)
            if b is None:
                return None
            return {
                "version": b.version,
                "built_hash": b.built_hash,
                "latest_hash": b.latest_hash,
                "repo": b.repo,
                "branch": b.branch,
                "repo_link": b.repo_link,
                "last_built_at": b.last_built_at.isoformat() if b.last_built_at else None,
            }

        sensors.append(
            KomodoOptionSensor(
                coordinator=coordinator,
                item_id=f"{entry_id}_{build.id}",
                extractor=state,
                key="build_state",
                device_info=create_build_device_info(build, base_url=coordinator.host_url),
                options=[s.name for s in BuildState],
                enabled_default=False,
                attributes_extractor=attributes,
            )
        )

    return sensors
