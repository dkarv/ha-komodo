from komodo_api.lib import KomodoClient, ApiKeyInitOptions
from komodo_api.types import GetVersion
from .coordinator import KomodoCoordinator
from homeassistant.core import HomeAssistant

class KomodoBase:
    _api: KomodoClient
    coordinator: KomodoCoordinator

    def __init__(self, hass: HomeAssistant, host: str, init_options: ApiKeyInitOptions) -> None:
        self._api = KomodoClient(host, init_options)
        self.coordinator = KomodoCoordinator(hass, self._api)


    async def close(self) -> None:
        """Close the API connection."""
        await self._api.close()


    async def test_connection(self) -> None:
        """Test the connection to the API."""
        
        try:
            await self._api.read.getVersion(GetVersion())
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Komodo API: {e}") from e

    async def first_refresh(self) -> None:
        if self.coordinator.data is None:
            await self.coordinator.async_config_entry_first_refresh()
    

