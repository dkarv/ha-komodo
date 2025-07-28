from komodo_api.lib import KomodoClient, ApiKeyInitOptions
from komodo_api.types import GetVersion
from .coordinator import KomodoCoordinator
from .const import normalize_host_url
from homeassistant.core import HomeAssistant

class KomodoBase:
    api: KomodoClient
    coordinator: KomodoCoordinator

    def __init__(self, hass: HomeAssistant, host: str, init_options: ApiKeyInitOptions) -> None:
        normalized_host = normalize_host_url(host)
        self.api = KomodoClient(normalized_host, init_options)
        self.coordinator = KomodoCoordinator(hass, self.api)


    async def close(self) -> None:
        """Close the API connection."""
        await self.api.close()


    async def test_connection(self) -> None:
        """Test the connection to the API."""
        
        try:
            await self.api.read.getVersion(GetVersion())
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Komodo API: {e}") from e

    async def first_refresh(self) -> None:
        if self.coordinator.data is None:
            await self.coordinator.async_config_entry_first_refresh()
    

