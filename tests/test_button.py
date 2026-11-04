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


def test_build_run_button(monkeypatch, mock_komodo_api):
    coordinator = MagicMock()
    coordinator.data = MagicMock()
    coordinator.async_request_refresh = AsyncMock()

    device_info = MagicMock()
    btn = button.KomodoBuildRunButton(
        coordinator=coordinator,
        api=mock_komodo_api,
        item_id="entry_b1",
        build_id="b1",
        build_name="jarvis-hub",
        device_info=device_info,
    )
    assert btn._attr_entity_registry_enabled_default is False
    assert btn._attr_unique_id == "entry_b1_run_button"
    assert btn._attr_name == "Run jarvis-hub build"

    mock_update = MagicMock()
    mock_komodo_api.execute.runBuild = AsyncMock(return_value=mock_update)

    called = {}
    async def fake_wait_for_completion(api, update, name):
        called['api'] = api
        called['update'] = update
        called['name'] = name
        return "done"
    monkeypatch.setattr(button, "wait_for_completion", fake_wait_for_completion)

    asyncio.run(btn.async_press())
    mock_komodo_api.execute.runBuild.assert_awaited_once_with(
        button.RunBuild(build="b1")
    )
    assert called['name'] == "Run build jarvis-hub"
    coordinator.async_request_refresh.assert_awaited_once()
