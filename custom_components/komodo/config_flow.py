"""Config flow for BWT Perla integration."""
import logging
from typing import Any

import voluptuous as vol

from komodo_api.lib import KomodoClient, ApiKeyInitOptions
from komodo_api.types import GetVersion
from komodo_api.exceptions import KomodoException
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from aiohttp import ClientConnectionError

from .const import DOMAIN, CONF_HOST, CONF_API_KEY, CONF_API_SECRET, normalize_host_url

_LOGGER = logging.getLogger(__name__)



def _komodo_schema(
        host: str | None = None,
        api_key: str | None = None,
        api_secret: str | None = None,
): return vol.Schema(
    {
        vol.Required(CONF_HOST, default=host): str,
        vol.Required(CONF_API_KEY, default=api_key): str,
        vol.Required(CONF_API_SECRET, default=api_secret): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from _komodo_schema with values provided by the user.
    """
    normalized_host = normalize_host_url(data[CONF_HOST])
    async with KomodoClient(normalized_host, ApiKeyInitOptions(data[CONF_API_KEY], data[CONF_API_SECRET])) as api:
       await api.read.getVersion(GetVersion())

    # Return info that you want to store in the config entry.
    return {"title": "Komodo"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Komodo."""

    VERSION = 1


    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                # Store the normalized host URL in the config entry
                normalized_data = user_input.copy()
                normalized_data[CONF_HOST] = normalize_host_url(user_input[CONF_HOST])
                return self.async_create_entry(title=info["title"], data=normalized_data)
            except ClientConnectionError:
                _LOGGER.exception("Connection error setting up the Komodo api")
                errors["base"] = "cannot_connect"
            except KomodoException as e:
                _LOGGER.exception("Api error setting up the Komodo api")
                if e.code == 401:
                    errors["base"] = "invalid_auth"
                    errors["details"] = e.error
                else:
                    errors["base"] = "unknown"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        schema = _komodo_schema() if user_input is None else _komodo_schema(
            user_input[CONF_HOST], user_input[CONF_API_KEY], user_input[CONF_API_SECRET],
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )
    

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Manual reconfiguration to change a setting."""
        current = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
                # Store the normalized host URL in the config entry
                normalized_data = user_input.copy()
                normalized_data[CONF_HOST] = normalize_host_url(user_input[CONF_HOST])
                self.hass.config_entries.async_update_entry(current, data=normalized_data)
                await self.hass.config_entries.async_reload(current.entry_id)
                return self.async_abort(reason="reconfiguration_successful")
#            except TODO:
#                _LOGGER.exception("Connection error setting up the Komodo Api")
#                errors["base"] = "cannot_connect"
#            except TODO:
#                _LOGGER.exception("Wrong authentication passed to Komodo api")
#                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="reconfigure", data_schema=_komodo_schema(
                host=current.data[CONF_HOST], 
                api_key=current.data[CONF_API_KEY],
                api_secret=current.data[CONF_API_SECRET],
            ), errors=errors
        )
