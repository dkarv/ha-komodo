from unittest.mock import MagicMock

from komodo_api.types import (
    ContainerListItem,
    ContainerStateStatusEnum,
    StackService,
    StackServiceState,
    StackServiceWithUpdate,
)

from custom_components.komodo.data.komodo_data import KomodoData
from custom_components.komodo.data.server import KomodoServer
from custom_components.komodo.data.service import KomodoUpdateInfo


def _stack_item(stack_id, services):
    item = MagicMock()
    item.id = stack_id
    item.name = stack_id
    item.info.server_id = "server_id"
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


def test_service_effective_image_and_installed_version():
    item = StackServiceWithUpdate(
        service="dind",
        image="sha256:e39da29cc49bd85cabdc2fcb223e8d565048cf47cf4af042022d15510badcacd",
        latest_image="docker:29-dind",
        update_available=True,
    )
    data = KomodoData()
    mock_stack = MagicMock()
    mock_stack.id = "s1"
    mock_stack.name = "paseo"
    mock_stack.info.server_id = "srv1"
    mock_stack.info.services = [item]
    data.add_stacks([mock_stack])

    dind = data.stacks["s1"].services["dind"]
    assert dind.effective_image == "docker:29-dind"

    # Before inspect, fallback is tag from effective_image
    assert dind.installed_version == "29-dind"

    # Apply env from inspect
    dind.env = ["DOCKER_VERSION=29.9.1"]
    assert dind.installed_version == "29.9.1"

    # Update info takes precedence once resolved
    uinfo = KomodoUpdateInfo(1234.0, current_version="29.9.1", new_version="29.9.3-dind")
    dind.update_info = uinfo
    assert dind.installed_version == "29.9.1"


def test_unassigned_stack_does_not_create_unknown_server_device():
    data = KomodoData()
    mock_stack = MagicMock()
    mock_stack.id = "s_unassigned"
    mock_stack.name = "pr-agent"
    mock_stack.info.server_id = ""
    mock_stack.info.server_name = ""
    mock_stack.info.services = []
    data.add_stacks([mock_stack])

    # No empty string key or unknown server added
    assert "" not in data.servers
    assert len(data.servers) == 0

    stack = data.stacks["s_unassigned"]
    assert stack.server_id is None


def test_add_builds_and_sensor():
    from komodo_api.types import BuildState

    from custom_components.komodo.sensors.build import (
        KomodoBuildStateSensor,
        create_build_sensors,
    )

    data = KomodoData()
    mock_build = MagicMock()
    mock_build.id = "b123"
    mock_build.name = "jarvis-backend"
    mock_build.info.state = BuildState.OK
    mock_build.info.version = "1.0.0"
    mock_build.info.built_hash = "abc12345"
    mock_build.info.latest_hash = "abc12345"
    mock_build.info.repo = "FaserF/Jarvis"
    mock_build.info.branch = "main"
    mock_build.info.repo_link = "https://github.com/FaserF/Jarvis"
    mock_build.info.last_built_at = "2026-11-04T05:00:00Z"
    mock_build.info.builder_id = "builder_1"

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
    assert isinstance(sensor, KomodoBuildStateSensor)
    assert sensor._attr_entity_registry_enabled_default is False
    assert sensor.native_value == "OK"
    attrs = sensor.extra_state_attributes
    assert attrs["version"] == "1.0.0"
    assert attrs["built_hash"] == "abc12345"
    assert attrs["repo"] == "FaserF/Jarvis"
    from custom_components.komodo.const import DOMAIN
    assert sensor._attr_device_info["identifiers"] == {(DOMAIN, "entry_1")}


def test_add_procedures_and_actions():
    from komodo_api.types import ActionState, ProcedureState

    from custom_components.komodo.sensors.automation import (
        KomodoActionStateSensor,
        KomodoProcedureStateSensor,
        create_automation_sensors,
    )

    data = KomodoData()
    mock_proc = MagicMock()
    mock_proc.id = "p1"
    mock_proc.name = "backup-db"
    mock_proc.info.state = ProcedureState.OK
    mock_proc.info.last_run_at = "2026-11-04T05:00:00Z"
    mock_proc.info.next_scheduled_run = "2026-11-05T05:00:00Z"
    mock_proc.info.schedule_error = None
    mock_proc.info.stages = ["stop", "dump", "start"]

    mock_act = MagicMock()
    mock_act.id = "a1"
    mock_act.name = "prune-cache"
    mock_act.info.state = ActionState.OK
    mock_act.info.last_run_at = "2026-11-04T05:30:00Z"
    mock_act.info.next_scheduled_run = None
    mock_act.info.schedule_error = None

    data.add_procedures([mock_proc])
    data.add_actions([mock_act])

    assert "p1" in data.procedures
    assert data.procedures["p1"].stages == 3
    assert "a1" in data.actions
    assert data.actions["a1"].name == "prune-cache"

    coordinator = MagicMock()
    coordinator.data = data
    coordinator.host_url = "https://komodo.example.com"
    sensors = create_automation_sensors(coordinator, "entry_1")
    assert len(sensors) == 2

    proc_sensor = next(s for s in sensors if isinstance(s, KomodoProcedureStateSensor))
    assert proc_sensor._attr_entity_registry_enabled_default is False
    assert proc_sensor.native_value == "OK"
    assert proc_sensor.extra_state_attributes["stages"] == 3

    act_sensor = next(s for s in sensors if isinstance(s, KomodoActionStateSensor))
    assert act_sensor._attr_entity_registry_enabled_default is False
    assert act_sensor.native_value == "OK"
    from custom_components.komodo.const import DOMAIN
    assert proc_sensor._attr_device_info["identifiers"] == {(DOMAIN, "entry_1")}
    assert act_sensor._attr_device_info["identifiers"] == {(DOMAIN, "entry_1")}


