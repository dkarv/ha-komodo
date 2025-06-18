"""Coordinator to fetch the data once for all sensors."""

import asyncio
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

_UPDATE_INTERVAL_MIN = 1
_UPDATE_INTERVAL_MAX = 30


class KomodoCoordinator(DataUpdateCoordinator[FIXME]):
    """Komodo coordinator."""

    def __init__(self, hass: HomeAssistant, my_api: KomodoClient) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="FIXME",
        )
        self.my_api = my_api

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        # Note: asyncio.TimeoutError and aiohttp.ClientError are already
        # handled by the data update coordinator.
        async with asyncio.timeout(10):
            # FIXME
            new_values = await self.my_api.get_current_data()
            return new_values
