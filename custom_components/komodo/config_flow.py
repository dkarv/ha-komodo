"""Config flow for BWT Perla integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_CODE, CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

def _komodo_schema(
        host: str | None = None,
        key: str | None = None,
        secret: str | None = None,
): return vol.Schema(
    {
        # FIXME
        vol.Required(CONF_HOST, default=host): str,
        vol.Required(CONF_CODE, default=code)   : str,
        vol.Required(CONF_CODE, default=code)   : str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from _komodo_schema with values provided by the user.
    """
    # FIXME
    async with KomodoClient(data[CONF_HOST], data[CONF_CODE]) as api:
       await api.get_current_data()

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
                return self.async_create_entry(title=info["title"], data=user_input)
            except TODO:
                _LOGGER.exception("Connection error setting up the Komodo api")
                errors["base"] = "cannot_connect"
            except TODO:
                _LOGGER.exception("Wrong user code passed to Komodo api")
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=_komodo_schema(), errors=errors
        )
    

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Manual reconfiguration to change a setting."""
        current = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
                self.hass.config_entries.async_update_entry(current, data=user_input)
                await self.hass.config_entries.async_reload(current.entry_id)
                return self.async_abort(reason="reconfiguration_successful")
            except TODO:
                _LOGGER.exception("Connection error setting up the Komodo Api")
                errors["base"] = "cannot_connect"
            except TODO:
                _LOGGER.exception("Wrong authentication passed to Komodo api")
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="reconfigure", data_schema=_komodo_schema(
                host=current.data[CONF_HOST], 
                code=current.data[CONF_CODE],
                TODO
            ), errors=errors
        )
