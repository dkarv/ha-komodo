import asyncio
import logging
from typing import Any

from komodo_api.lib import KomodoClient, ApiKeyInitOptions, CancelToken
from komodo_api.types import GetVersion
from homeassistant.core import HomeAssistant
from .coordinator import KomodoCoordinator
from .utils import fix_host

_LOGGER = logging.getLogger(__name__)


class KomodoBase:
    """Base class for Komodo integration, holding shared API client and coordinator."""

    api: KomodoClient
    coordinator: KomodoCoordinator
    container_categories: frozenset[str]
    hass: HomeAssistant
    entry_id: str | None
    ws_cancel_token: CancelToken
    ws_task: asyncio.Task[Any] | None

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        init_options: ApiKeyInitOptions,
        entry_id: str | None = None,
    ) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self.api = KomodoClient(host, init_options)
        self.coordinator = KomodoCoordinator(hass, self.api)
        self.coordinator.host_url = fix_host(host)
        self.container_categories = frozenset()
        self.ws_cancel_token = CancelToken()
        self.ws_task = None

    def start_websocket(self) -> None:
        """Start real-time WebSocket update listener in background."""
        if self.ws_task is not None and not self.ws_task.done():
            return

        def _on_update(update_item: Any) -> None:
            _LOGGER.debug("Real-time update received from Komodo WebSocket: %s", update_item)
            if hasattr(self.hass, "loop") and self.hass.loop.is_running():
                self.hass.loop.call_soon_threadsafe(
                    lambda: self.hass.async_create_task(
                        self.coordinator.async_request_refresh()
                    )
                )

        async def _run_ws() -> None:
            _LOGGER.info("Starting Komodo WebSocket real-time subscription")
            try:
                await self.api.subscribe_to_update_websocket(
                    on_update=_on_update,
                    retry=True,
                    retry_timeout_ms=5000,
                    cancel=self.ws_cancel_token,
                )
            except asyncio.CancelledError:
                _LOGGER.debug("Komodo WebSocket task cancelled")
            except Exception as err:
                _LOGGER.warning("Komodo WebSocket closed with error: %s", err)

        task_name = f"komodo_ws_{self.entry_id}" if self.entry_id else "komodo_ws"
        if hasattr(self.hass, "async_create_background_task"):
            self.ws_task = self.hass.async_create_background_task(
                _run_ws(), name=task_name
            )
        else:
            self.ws_task = self.hass.async_create_task(_run_ws())

    async def stop_websocket(self) -> None:
        """Stop the real-time WebSocket listener."""
        if self.ws_cancel_token:
            self.ws_cancel_token.cancel()
        if self.ws_task is not None:
            if not self.ws_task.done():
                self.ws_task.cancel()
                try:
                    await self.ws_task
                except (asyncio.CancelledError, Exception):
                    pass
            self.ws_task = None

    async def close(self) -> None:
        """Close the API connection and terminate websocket."""
        await self.stop_websocket()
        await self.api.close()

    async def test_connection(self) -> None:
        """Test the connection to the API and record Komodo version."""
        try:
            version_res = await self.api.read.getVersion(GetVersion())
            if version_res and hasattr(version_res, "version"):
                self.coordinator.komodo_version = version_res.version
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Komodo API: {e}") from e
