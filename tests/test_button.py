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

@pytest.mark.asyncio
async def test_button_entity_creation(mock_komodo_api, mock_procedure):
    entity = button.KomodoProcedureButton(mock_komodo_api, "entry_id", mock_procedure)
    assert entity.entity_id == "button.komodo_button_test_id"
    assert entity._attr_unique_id == "entry_id_button_test_id"
    assert entity._attr_name == "Procedure Test Procedure"

@pytest.mark.asyncio
async def test_async_press_calls_runProcedure(monkeypatch, mock_komodo_api, mock_procedure):
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

    result = await entity.async_press()
    mock_komodo_api.execute.runProcedure.assert_awaited_once_with(
        button.RunProcedure(procedure=mock_procedure.id)
    )
    assert called['api'] == mock_komodo_api
    assert called['update'] == mock_update
    assert called['name'] == "Procedure Test Procedure"
