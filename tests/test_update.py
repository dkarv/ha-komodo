from unittest.mock import MagicMock

from komodo_api.types import StackServiceWithUpdate

from custom_components.komodo.data.komodo_data import KomodoData
from custom_components.komodo.data.service import KomodoUpdateInfo
from custom_components.komodo.update import KomodoUpdateEntity


def _coordinator():
    coord = MagicMock()
    data = KomodoData()
    coord.data = data
    return coord


def test_update_entity_with_pending_update():
    coord = _coordinator()
    stack = MagicMock()
    stack.id = "s1"
    stack.name = "paseo"
    stack.info.server_id = "srv1"
    svc_item = StackServiceWithUpdate(
        service="dind",
        image="sha256:e39da29cc49bd85cabdc2fcb223e8d565048cf47cf4af042022d15510badcacd",
        latest_image="docker:29-dind",
        update_available=True,
    )
    stack.info.services = [svc_item]
    coord.data.add_stacks([stack])

    dind = coord.data.stacks["s1"].services["dind"]
    dind.env = ["DOCKER_VERSION=29.9.1"]
    uinfo = KomodoUpdateInfo(100.0, current_version="29.9.1", new_version="29.9.3-dind")
    uinfo.release_summary = "Docker 29.9.3"
    uinfo.release_url = "https://github.com/docker-library/docker"
    dind.update_info = uinfo

    entity = KomodoUpdateEntity(
        coordinator=coord,
        item_id="entry_s1_dind",
        stack_id="s1",
        stack_name="paseo",
        service_name="dind",
        device_info=MagicMock(),
    )

    assert entity.installed_version == "29.9.1"
    assert entity.latest_version == "29.9.3-dind"
    assert entity.has_update is True
    assert entity.release_summary == "Docker 29.9.3"
    assert entity.release_url == "https://github.com/docker-library/docker"


def test_update_entity_up_to_date():
    coord = _coordinator()
    stack = MagicMock()
    stack.id = "s1"
    stack.name = "jarvis"
    stack.info.server_id = "srv1"
    svc_item = StackServiceWithUpdate(
        service="redis",
        image="redis:7-alpine",
        latest_image="redis:7-alpine",
        update_available=False,
    )
    stack.info.services = [svc_item]
    coord.data.add_stacks([stack])

    redis_svc = coord.data.stacks["s1"].services["redis"]
    redis_svc.env = ["REDIS_VERSION=7.4.12"]

    entity = KomodoUpdateEntity(
        coordinator=coord,
        item_id="entry_s1_redis",
        stack_id="s1",
        stack_name="jarvis",
        service_name="redis",
        device_info=MagicMock(),
    )

    assert entity.installed_version == "7.4.12"
    assert entity.latest_version == "7.4.12"
    assert entity.has_update is False


def test_update_entity_release_notes_fallback():
    coord = _coordinator()
    stack = MagicMock()
    stack.id = "s1"
    stack.name = "jarvis"
    stack.info.server_id = "srv1"
    svc_item = StackServiceWithUpdate(
        service="tailscale",
        image="tailscale/tailscale:latest",
        latest_image="tailscale/tailscale:latest",
        update_available=True,
    )
    stack.info.services = [svc_item]
    coord.data.add_stacks([stack])

    svc = coord.data.stacks["s1"].services["tailscale"]
    svc.labels = {"org.opencontainers.image.version": "1.78.0"}
    up_info = KomodoUpdateInfo(updated_at=100.0, current_version="1.78.0", new_version="1.80.0")
    up_info.release_url = "https://hub.docker.com/r/tailscale/tailscale/tags"
    svc.update_info = up_info

    entity = KomodoUpdateEntity(
        coordinator=coord,
        item_id="entry_s1_tailscale",
        stack_id="s1",
        stack_name="jarvis",
        service_name="tailscale",
        device_info=MagicMock(),
    )

    assert entity.has_update is True
    assert entity.release_url == "https://hub.docker.com/r/tailscale/tailscale/tags"
    notes = entity.release_notes()
    assert notes is not None
    assert "Update available for tailscale" in notes
    assert "[View Changelog / Release Notes](https://hub.docker.com/r/tailscale/tailscale/tags)" in notes

