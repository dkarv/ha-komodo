from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.komodo.const import DOMAIN
from custom_components.komodo.services import (
    SERVICE_GLOBAL_AUTO_UPDATE,
    SERVICE_PRUNE_DOCKER,
    SERVICE_RESTART_ALL_CONTAINERS,
    async_setup_services,
)


def _server(id, name, state="OK"):
    server = MagicMock(id=id, state=state)
    server.name = name
    return server


def _add_instance(hass, entry_id, servers, state=ConfigEntryState.LOADED):
    """Add a Komodo config entry with a mocked API and a device per server."""
    entry = MockConfigEntry(domain=DOMAIN, entry_id=entry_id, title=entry_id, state=state)
    entry.add_to_hass(hass)

    komodo = MagicMock()
    komodo.api.execute = MagicMock()
    komodo.coordinator.data.servers = {s.id: s for s in servers}
    komodo.coordinator.async_request_refresh = AsyncMock()
    hass.data.setdefault(DOMAIN, {})[entry_id] = komodo

    device_reg = dr.async_get(hass)
    devices = {
        s.id: device_reg.async_get_or_create(
            config_entry_id=entry_id,
            identifiers={(DOMAIN, s.id)},
            name=s.name,
            model="Server",
        ).id
        for s in servers
    }
    return komodo, devices


def _update(success=True):
    return MagicMock(success=success)


@pytest.fixture
def wait():
    """Make wait_for_completion return the update it was given."""
    async def passthrough(api, update, title):
        return update

    with patch(
        "custom_components.komodo.services.wait_for_completion", side_effect=passthrough
    ) as mock:
        yield mock


@pytest.fixture
async def setup(hass):
    async_setup_services(hass)


async def test_services_registered(hass, setup):
    for service in (
        SERVICE_PRUNE_DOCKER,
        SERVICE_RESTART_ALL_CONTAINERS,
        SERVICE_GLOBAL_AUTO_UPDATE,
    ):
        assert hass.services.has_service(DOMAIN, service)


@pytest.mark.parametrize(
    ("prune_type", "method"),
    [
        ("images", "pruneImages"),
        ("containers", "pruneContainers"),
        ("volumes", "pruneVolumes"),
        ("buildx", "pruneBuildx"),
        ("system", "pruneSystem"),
    ],
)
async def test_prune_docker(hass, setup, wait, prune_type, method):
    komodo, devices = _add_instance(hass, "e1", [_server("srv1", "vm")])
    api_call = AsyncMock(return_value=_update())
    setattr(komodo.api.execute, method, api_call)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_PRUNE_DOCKER,
        {"server": [devices["srv1"]], "prune_type": prune_type},
        blocking=True,
    )

    api_call.assert_awaited_once()
    assert api_call.await_args.args[0].server == "srv1"
    komodo.coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.parametrize(
    "data",
    [
        {},  # no server, no type: must not prune anything anywhere
        {"server": []},
        {"prune_type": "images"},
        {"server": ["x"]},  # prune_type is required
        {"server": ["x"], "prune_type": "image"},  # typo must not fall back to system
    ],
)
async def test_prune_docker_rejects_invalid_input(hass, setup, data):
    komodo, _ = _add_instance(hass, "e1", [_server("srv1", "vm")])

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(DOMAIN, SERVICE_PRUNE_DOCKER, data, blocking=True)

    komodo.api.execute.pruneSystem.assert_not_called()


async def test_servers_across_instances(hass, setup, wait):
    """Each selected server is pruned by the Komodo instance it belongs to."""
    k1, d1 = _add_instance(hass, "e1", [_server("a", "vm-a")])
    k2, d2 = _add_instance(hass, "e2", [_server("b", "vm-b")])
    k1.api.execute.restartAllContainers = AsyncMock(return_value=_update())
    k2.api.execute.restartAllContainers = AsyncMock(return_value=_update())

    await hass.services.async_call(
        DOMAIN,
        SERVICE_RESTART_ALL_CONTAINERS,
        {"server": [d1["a"], d2["b"]]},
        blocking=True,
    )

    assert k1.api.execute.restartAllContainers.await_args.args[0].server == "a"
    assert k2.api.execute.restartAllContainers.await_args.args[0].server == "b"
    k1.coordinator.async_request_refresh.assert_awaited_once()
    k2.coordinator.async_request_refresh.assert_awaited_once()


async def test_non_server_device_rejected(hass, setup):
    komodo, _ = _add_instance(hass, "e1", [_server("srv1", "vm")])
    stack_device = dr.async_get(hass).async_get_or_create(
        config_entry_id="e1", identifiers={(DOMAIN, "stack1")}, name="web"
    )

    with pytest.raises(ServiceValidationError, match="not a Komodo server"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_RESTART_ALL_CONTAINERS,
            {"server": [stack_device.id]},
            blocking=True,
        )
    komodo.api.execute.restartAllContainers.assert_not_called()


async def test_placeholder_server_rejected(hass, setup):
    _, devices = _add_instance(hass, "e1", [_server("gone", "Unknown Server gone", state=None)])

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_RESTART_ALL_CONTAINERS,
            {"server": [devices["gone"]]},
            blocking=True,
        )


async def test_unloaded_instance_rejected(hass, setup):
    _, devices = _add_instance(
        hass, "e1", [_server("srv1", "vm")], state=ConfigEntryState.NOT_LOADED
    )

    with pytest.raises(ServiceValidationError, match="not loaded"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_RESTART_ALL_CONTAINERS,
            {"server": [devices["srv1"]]},
            blocking=True,
        )


async def test_failed_update_raises_after_running_all(hass, setup, wait):
    """A failed Komodo update fails the call, but the other servers still run."""
    komodo, devices = _add_instance(hass, "e1", [_server("a", "vm-a"), _server("b", "vm-b")])
    komodo.api.execute.pruneImages = AsyncMock(
        side_effect=[_update(success=False), _update()]
    )

    with pytest.raises(HomeAssistantError, match="Prune images on vm-a: failed"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_PRUNE_DOCKER,
            {"server": [devices["a"], devices["b"]], "prune_type": "images"},
            blocking=True,
        )

    assert komodo.api.execute.pruneImages.await_count == 2
    komodo.coordinator.async_request_refresh.assert_awaited_once()


async def test_api_error_raises(hass, setup, wait):
    komodo, devices = _add_instance(hass, "e1", [_server("srv1", "vm")])
    komodo.api.execute.restartAllContainers = AsyncMock(side_effect=RuntimeError("boom"))

    with pytest.raises(HomeAssistantError, match="boom"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_RESTART_ALL_CONTAINERS,
            {"server": [devices["srv1"]]},
            blocking=True,
        )


async def test_global_auto_update(hass, setup, wait):
    k1, _ = _add_instance(hass, "e1", [])
    k2, _ = _add_instance(hass, "e2", [])
    k1.api.execute.globalAutoUpdate = AsyncMock(return_value=_update())
    k2.api.execute.globalAutoUpdate = AsyncMock(return_value=_update())

    await hass.services.async_call(
        DOMAIN,
        SERVICE_GLOBAL_AUTO_UPDATE,
        {"config_entry_id": "e2", "skip_auto_update": True},
        blocking=True,
    )

    k1.api.execute.globalAutoUpdate.assert_not_called()
    assert k2.api.execute.globalAutoUpdate.await_args.args[0].skip_auto_update is True


async def test_global_auto_update_requires_instance(hass, setup):
    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN, SERVICE_GLOBAL_AUTO_UPDATE, {}, blocking=True
        )


async def test_global_auto_update_rejects_other_domain(hass, setup):
    MockConfigEntry(domain="other", entry_id="x").add_to_hass(hass)

    with pytest.raises(ServiceValidationError, match="not a Komodo config entry"):
        await hass.services.async_call(
            DOMAIN, SERVICE_GLOBAL_AUTO_UPDATE, {"config_entry_id": "x"}, blocking=True
        )
