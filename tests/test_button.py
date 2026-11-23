import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

import custom_components.komodo.button as button

@pytest.fixture
def mock_komodo_api():
    api = MagicMock()
    api.execute.runProcedure = AsyncMock()
    return api

@pytest.fixture
def mock_procedure():
    class Procedure:
        id = "test_id"
        name = "Test Procedure"
    return Procedure()

def test_button_entity_creation(mock_komodo_api, mock_procedure):
    entity = button.KomodoProcedureButton(mock_komodo_api, "entry_id", mock_procedure)
    assert entity.entity_id == "button.komodo_button_test_id"
    assert entity._attr_unique_id == "entry_id_button_test_id"
    assert entity._attr_name == "Procedure Test Procedure"

def test_async_press_calls_runProcedure(monkeypatch, mock_komodo_api, mock_procedure):
    entity = button.KomodoProcedureButton(mock_komodo_api, "entry_id", mock_procedure)
    mock_update = MagicMock()
    mock_komodo_api.execute.runProcedure.return_value = mock_update

    # Patch wait_for_completion
    called = {}
    async def fake_wait_for_completion(api, update, name):
        called['api'] = api
        called['update'] = update
        called['name'] = name
        return "done"
    monkeypatch.setattr(button, "wait_for_completion", fake_wait_for_completion)

    asyncio.run(entity.async_press())
    mock_komodo_api.execute.runProcedure.assert_awaited_once_with(
        button.RunProcedure(procedure=mock_procedure.id)
    )
    assert called['api'] == mock_komodo_api
    assert called['update'] == mock_update
    assert called['name'] == "Procedure Test Procedure"


def _coordinator(**data):
    coordinator = MagicMock()
    coordinator.data = MagicMock(**data)
    coordinator.host_url = "https://komodo.example.com"
    coordinator.server_device_ids = {}
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


def _resource(id, name, **attrs):
    r = MagicMock(id=id, **attrs)
    r.name = name
    return r


def _fake_wait(monkeypatch):
    called = {}

    async def fake_wait_for_completion(api, update, name):
        called["update"] = update
        called["name"] = name

    monkeypatch.setattr(button, "wait_for_completion", fake_wait_for_completion)
    return called


def test_build_run_button(monkeypatch, mock_komodo_api):
    build = _resource("b1", "jarvis-hub", version="1.2.3", built_hash=None)
    coordinator = _coordinator(builds={"b1": build})

    [btn] = button.create_build_buttons(coordinator, mock_komodo_api, "entry")
    assert btn._attr_entity_registry_enabled_default is False
    assert btn._attr_unique_id == "entry_b1_run_button"
    assert btn._attr_name == "Run jarvis-hub build"

    mock_update = MagicMock()
    mock_komodo_api.execute.runBuild = AsyncMock(return_value=mock_update)
    called = _fake_wait(monkeypatch)

    asyncio.run(btn.async_press())
    mock_komodo_api.execute.runBuild.assert_awaited_once_with(
        button.RunBuild(build="b1")
    )
    assert called["update"] == mock_update
    assert called["name"] == "Run jarvis-hub build"
    coordinator.async_request_refresh.assert_awaited_once()


def test_stack_deploy_button(monkeypatch, mock_komodo_api):
    stack = _resource("s1", "web", server_id=None, deployed_hash=None, branch=None)
    coordinator = _coordinator(stacks={"s1": stack})

    [btn] = button.create_deploy_buttons_for_stacks(coordinator, mock_komodo_api, "entry")
    assert btn._attr_entity_registry_enabled_default is True
    assert btn._attr_unique_id == "entry_s1_deploy_button"
    assert btn._attr_name == "Deploy web stack"

    mock_komodo_api.execute.deployStack = AsyncMock()
    _fake_wait(monkeypatch)

    asyncio.run(btn.async_press())
    mock_komodo_api.execute.deployStack.assert_awaited_once_with(
        button.DeployStack(stack="s1")
    )
    coordinator.async_request_refresh.assert_awaited_once()
