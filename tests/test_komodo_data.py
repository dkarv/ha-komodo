from unittest.mock import MagicMock

from komodo_api.types import (
    ContainerListItem,
    ContainerStateStatusEnum,
    StackServiceState,
    StackServiceWithUpdate,
    StackService,
)

from custom_components.komodo.data.komodo_data import KomodoData
from custom_components.komodo.data.server import KomodoServer
from custom_components.komodo.data.service import KomodoUpdateInfo


def _stack_item(stack_id, services, server_id="server_id"):
    item = MagicMock()
    item.id = stack_id
    item.name = stack_id
    item.info.server_id = server_id
    item.info.services = [
        StackServiceWithUpdate(service=name, image=f"{name}:1", update_available=update)
        for name, update in services
    ]
    return item


def _stack_service(stack_id, service, container=None):
    return StackService(
        stack_id=stack_id,
        service=service,
        image=f"{service}:1",
        container=container,
        state=StackServiceState.RUNNING if container else StackServiceState.DOWN,
    )


def test_add_stack_services_applies_container():
    data = KomodoData()
    data.add_stacks([_stack_item("s1", [("web", True), ("db", False)])])
    data.add_stack_services([
        _stack_service("s1", "web", ContainerListItem(
            name="s1-web-1",
            id="abc",
            image="ghcr.io/org/web:latest",
            state=ContainerStateStatusEnum.RUNNING,
        )),
        _stack_service("s1", "db"),
        # Unknown stack / service are ignored
        _stack_service("other", "web", ContainerListItem(name="x", state=ContainerStateStatusEnum.RUNNING)),
        _stack_service("s1", "gone", ContainerListItem(name="y", state=ContainerStateStatusEnum.RUNNING)),
    ])

    web = data.stacks["s1"].services["web"]
    assert web.state == ContainerStateStatusEnum.RUNNING
    assert web.container_id == "abc"
    assert web.image == "ghcr.io/org/web:latest"
    assert web.has_container

    db = data.stacks["s1"].services["db"]
    assert db.state is None
    assert db.image == "db:1"
    assert not db.has_container


def test_update_info_current_version_from_labels():
    info = KomodoUpdateInfo(0)
    assert info.current_version == "0"
    info.apply_labels({"org.opencontainers.image.version": "1.2.3"})
    assert info.current_version == "1.2.3"
    info.apply_labels({})
    assert info.current_version == "0"


def test_server_stats_from_list_item():
    item = MagicMock()
    item.info.stats.cpu_perc = 12.5
    item.info.stats.mem_used_gb = 4.0
    item.info.stats.mem_total_gb = 16.0
    item.info.stats.disk_used_gb = 100.0
    item.info.stats.disk_total_gb = 400.0
    item.info.stats.load_average.one = 0.7
    server = KomodoServer(item)
    assert server.cpu_percent == 12.5
    assert server.memory_percent == 25.0
    assert server.disk_percent == 25.0
    assert server.disk_free_gb == 300.0
    assert server.load_average_1m == 0.7


def test_server_without_stats():
    item = MagicMock()
    item.info.stats = None
    server = KomodoServer(item)
    assert server.cpu_percent is None
    assert server.disk_percent is None


def test_unassigned_stack_creates_no_unknown_server():
    data = KomodoData()
    data.add_stacks([_stack_item("s1", [("web", False)], server_id="")])
    assert data.servers == {}
    assert data.stacks["s1"].server_id is None


def test_stack_on_missing_server_creates_unknown_server():
    data = KomodoData()
    data.add_stacks([_stack_item("s1", [("web", False)], server_id="gone")])
    server = data.servers["gone"]
    assert server.name == "Unknown Server gone"
    assert server.stack_count == 1


def test_add_builds_and_sensor():
    from komodo_api.types import BuildState
    from custom_components.komodo.sensors.build import create_build_sensors
    from custom_components.komodo.sensors.common import KomodoOptionSensor

    data = KomodoData()
    mock_build = MagicMock()
    mock_build.id = "b123"
    mock_build.name = "jarvis-backend"
    mock_build.info.state = BuildState.OK
    mock_build.info.version = MagicMock(major=1, minor=0, patch=0)
    mock_build.info.built_hash = "abc12345"
    mock_build.info.latest_hash = "abc12345"
    mock_build.info.repo = "FaserF/Jarvis"
    mock_build.info.branch = "main"
    mock_build.info.repo_link = "https://github.com/FaserF/Jarvis"
    mock_build.info.last_built_at = 1793768400000  # 2026-11-04T05:00:00Z

    data.add_builds([mock_build])
    assert "b123" in data.builds
    b = data.builds["b123"]
    assert b.name == "jarvis-backend"
    assert b.version == "1.0.0"
    assert b.state == BuildState.OK

    coordinator = MagicMock()
    coordinator.data = data
    coordinator.host_url = "https://komodo.example.com"
    sensors = create_build_sensors(coordinator, "entry_1")
    assert len(sensors) == 1
    sensor = sensors[0]
    assert isinstance(sensor, KomodoOptionSensor)
    assert sensor._attr_unique_id == "entry_1_b123_build_state"
    assert sensor._attr_entity_registry_enabled_default is False
    assert sensor.native_value == "OK"
    attrs = sensor.extra_state_attributes
    assert attrs["version"] == "1.0.0"
    assert attrs["built_hash"] == "abc12345"
    assert attrs["repo"] == "FaserF/Jarvis"
    assert attrs["last_built_at"] == "2026-11-04T05:00:00+00:00"

    # Build removed from Komodo: sensor reports UNKNOWN instead of failing.
    data.builds.clear()
    assert sensor._extractor(data) == "UNKNOWN"
    assert sensor.extra_state_attributes is None


def test_unversioned_never_built_build():
    from komodo_api.types import BuildState

    data = KomodoData()
    mock_build = MagicMock()
    mock_build.id = "b1"
    mock_build.name = "x"
    mock_build.info.state = BuildState.UNKNOWN
    mock_build.info.version = MagicMock(major=0, minor=0, patch=0)
    mock_build.info.last_built_at = 0
    mock_build.info.built_hash = None
    mock_build.info.repo = ""
    mock_build.info.branch = ""
    mock_build.info.repo_link = ""
    data.add_builds([mock_build])
    b = data.builds["b1"]
    assert b.version is None
    assert b.last_built_at is None
    assert b.repo is None
