import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from custom_components.komodo.const import DOMAIN
from custom_components.komodo.services import (
    SERVICE_PRUNE_DOCKER,
    SERVICE_RESTART_ALL_CONTAINERS,
    SERVICE_GLOBAL_AUTO_UPDATE,
    async_setup_services,
    async_unload_services,
)
from custom_components.komodo.base import KomodoBase


@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.data = {DOMAIN: {}}
    services = {}

    def async_register(domain, service, handler):
        services[(domain, service)] = handler

    def async_remove(domain, service):
        services.pop((domain, service), None)

    def has_service(domain, service):
        return (domain, service) in services

    hass.services.async_register = MagicMock(side_effect=async_register)
    hass.services.async_remove = MagicMock(side_effect=async_remove)
    hass.services.has_service = MagicMock(side_effect=has_service)
    hass._services = services
    return hass


@pytest.fixture
def mock_komodo(mock_hass):
    komodo = MagicMock(spec=KomodoBase)
    komodo.api = MagicMock()
    komodo.api.execute.pruneSystem = AsyncMock()
    komodo.api.execute.pruneImages = AsyncMock()
    komodo.api.execute.pruneContainers = AsyncMock()
    komodo.api.execute.pruneVolumes = AsyncMock()
    komodo.api.execute.pruneBuildx = AsyncMock()
    komodo.api.execute.restartAllContainers = AsyncMock()
    komodo.api.execute.globalAutoUpdate = AsyncMock()

    mock_server = MagicMock()
    mock_server.id = "srv_1"
    mock_server.name = "oracle-vm"
    mock_server.is_unknown = False

    komodo.coordinator = MagicMock()
    komodo.coordinator.data = MagicMock()
    komodo.coordinator.data.servers = {"srv_1": mock_server}
    komodo.coordinator.async_request_refresh = AsyncMock()

    mock_hass.data[DOMAIN]["entry_1"] = komodo
    return komodo


def test_service_setup_and_unload(mock_hass):
    asyncio.run(async_setup_services(mock_hass))
    assert mock_hass.services.has_service(DOMAIN, SERVICE_PRUNE_DOCKER)
    assert mock_hass.services.has_service(DOMAIN, SERVICE_RESTART_ALL_CONTAINERS)
    assert mock_hass.services.has_service(DOMAIN, SERVICE_GLOBAL_AUTO_UPDATE)

    # Empty entries and unload
    mock_hass.data[DOMAIN].clear()
    asyncio.run(async_unload_services(mock_hass))
    assert not mock_hass.services.has_service(DOMAIN, SERVICE_PRUNE_DOCKER)


def test_prune_docker_service(mock_hass, mock_komodo):
    asyncio.run(async_setup_services(mock_hass))
    prune_handler = mock_hass._services[(DOMAIN, SERVICE_PRUNE_DOCKER)]

    with patch("custom_components.komodo.services.wait_for_completion", AsyncMock()):
        # 1. Prune system on all servers (omitted server param)
        call = MagicMock()
        call.data = {"prune_type": "system"}
        asyncio.run(prune_handler(call))
        assert mock_komodo.api.execute.pruneSystem.await_count == 1

        # 2. Prune images by server name
        call = MagicMock()
        call.data = {"server": "oracle-vm", "prune_type": "images"}
        asyncio.run(prune_handler(call))
        assert mock_komodo.api.execute.pruneImages.await_count == 1

        # 3. Prune containers by server id
        call = MagicMock()
        call.data = {"server": "srv_1", "prune_type": "containers"}
        asyncio.run(prune_handler(call))
        assert mock_komodo.api.execute.pruneContainers.await_count == 1

        # 4. Prune volumes
        call = MagicMock()
        call.data = {"server": "srv_1", "prune_type": "volumes"}
        asyncio.run(prune_handler(call))
        assert mock_komodo.api.execute.pruneVolumes.await_count == 1

        # 5. Prune buildx
        call = MagicMock()
        call.data = {"server": "srv_1", "prune_type": "buildx"}
        asyncio.run(prune_handler(call))
        assert mock_komodo.api.execute.pruneBuildx.await_count == 1


def test_restart_all_containers_service(mock_hass, mock_komodo):
    asyncio.run(async_setup_services(mock_hass))
    restart_handler = mock_hass._services[(DOMAIN, SERVICE_RESTART_ALL_CONTAINERS)]

    with patch("custom_components.komodo.services.wait_for_completion", AsyncMock()):
        call = MagicMock()
        call.data = {"server": "oracle-vm"}
        asyncio.run(restart_handler(call))
        assert mock_komodo.api.execute.restartAllContainers.await_count == 1


def test_global_auto_update_service(mock_hass, mock_komodo):
    asyncio.run(async_setup_services(mock_hass))
    update_handler = mock_hass._services[(DOMAIN, SERVICE_GLOBAL_AUTO_UPDATE)]

    with patch("custom_components.komodo.services.wait_for_completion", AsyncMock()):
        call = MagicMock()
        call.data = {"skip_auto_update": True}
        asyncio.run(update_handler(call))
        assert mock_komodo.api.execute.globalAutoUpdate.await_count == 1
