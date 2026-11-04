import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from custom_components.komodo.base import KomodoBase
from komodo_api.lib import ApiKeyInitOptions


@pytest.fixture
def mock_base():
    hass = MagicMock()
    hass.loop.is_running.return_value = True

    tasks = []
    def create_task(coro, name=None):
        t = asyncio.create_task(coro)
        tasks.append(t)
        return t

    hass.async_create_background_task = MagicMock(side_effect=create_task)
    hass.async_create_task = MagicMock(side_effect=create_task)
    hass.loop.call_soon_threadsafe = MagicMock(side_effect=lambda fn: fn())

    with patch("custom_components.komodo.base.KomodoClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_client.subscribe_to_update_websocket = AsyncMock()
        mock_client_cls.return_value = mock_client

        base = KomodoBase(hass, "http://localhost:9120", ApiKeyInitOptions("k", "s"), entry_id="test_entry")
        base.coordinator.async_request_refresh = AsyncMock()
        yield base


def test_start_and_stop_websocket(mock_base):
    async def run_test():
        # Start websocket
        mock_base.start_websocket()
        assert mock_base.ws_task is not None
        await asyncio.sleep(0.05)
        mock_base.api.subscribe_to_update_websocket.assert_called_once()

        # Extract on_update callback
        kwargs = mock_base.api.subscribe_to_update_websocket.call_args.kwargs
        on_update = kwargs["on_update"]

        # Trigger update callback
        on_update({"type": "StackDeployed"})
        await asyncio.sleep(0.01)
        mock_base.coordinator.async_request_refresh.assert_awaited()

        # Stop websocket
        await mock_base.stop_websocket()
        assert mock_base.ws_cancel_token.cancelled is True
        assert mock_base.ws_task is None

    asyncio.run(run_test())


def test_close_stops_websocket(mock_base):
    async def run_test():
        mock_base.start_websocket()
        await mock_base.close()
        assert mock_base.ws_cancel_token.cancelled is True
        mock_base.api.close.assert_awaited_once()

    asyncio.run(run_test())
