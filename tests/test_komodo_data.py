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
