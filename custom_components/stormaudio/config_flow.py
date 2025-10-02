"""Config flow for StormAudio integration."""
import asyncio
import logging
from typing import Any, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, DEFAULT_PORT, DEFAULT_NAME

_LOGGER = logging.getLogger(__name__)


class StormAudioConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for StormAudio."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            
            # Test connection
            if await self._test_connection(host, port):
                # Check if already configured
                await self.async_set_unique_id(f"{host}:{port}")
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input
                )
            else:
                errors["base"] = "cannot_connect"
        
        data_schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.port,
            vol.Required(CONF_NAME, default=DEFAULT_NAME): str
        })
        
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors
        )

    async def _test_connection(self, host: str, port: int) -> bool:
        """Test connection to StormAudio device."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=5
            )
            
            writer.write(b"ssp.power\n")
            await writer.drain()
            
            response = await asyncio.wait_for(reader.readline(), timeout=5)
            
            writer.close()
            await writer.wait_closed()
            
            return len(response) > 0
            
        except Exception as e:
            _LOGGER.error("Connection test failed: %s", e)
            return False
