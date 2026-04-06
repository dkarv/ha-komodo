from komodo_api.lib import KomodoClient, ApiKeyInitOptions
from komodo_api.types import GetVersion
from homeassistant.core import HomeAssistant
from .coordinator import KomodoCoordinator


class KomodoBase:
    """Base class for Komodo integration, holding shared API client and coordinator."""
    api: KomodoClient
    coordinator: KomodoCoordinator

    def __init__(
        self, hass: HomeAssistant, host: str, init_options: ApiKeyInitOptions
    ) -> None:
        self.api = KomodoClient(host, init_options)
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
