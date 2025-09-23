"""Data update coordinator for StormAudio integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, TIMEOUT

_LOGGER = logging.getLogger(__name__)


class StormAudioCoordinator(DataUpdateCoordinator):
    """Class to manage fetching StormAudio data."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        scan_interval: int,
    ) -> None:
        """Initialize the coordinator."""
        self.host = host
        self.port = port
        self.connection = StormAudioConnection(host, port)
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            # Get power status
            power_response = await self.connection.send_command("POWER?")
            if not power_response:
                raise UpdateFailed("Could not connect to StormAudio device")

            data = {
                "available": True,
                "power": "ON" in power_response.upper(),
            }

            # Only get other data if powered on
            if data["power"]:
                # Get volume
                volume_response = await self.connection.send_command("VOLUME?")
                if volume_response:
                    try:
                        volume_parts = volume_response.split()
                        if len(volume_parts) >= 2:
                            db_value = float(volume_parts[1])
                            # Convert from dB (-80 to 0) to 0-1 range
                            data["volume_level"] = max(0.0, min(1.0, (db_value + 80) / 80))
                    except (ValueError, IndexError):
                        data["volume_level"] = 0.5

                # Get mute status
                mute_response = await self.connection.send_command("MUTE?")
                data["muted"] = mute_response and "ON" in mute_response.upper()

                # Get input
                input_response = await self.connection.send_command("INPUT?")
                if input_response:
                    try:
                        input_parts = input_response.split()
                        if len(input_parts) >= 2:
                            data["input"] = int(input_parts[1])
                    except (ValueError, IndexError):
                        data["input"] = 1

                # Get preset
                preset_response = await self.connection.send_command("PRESET?")
                if preset_response:
                    try:
                        preset_parts = preset_response.split()
                        if len(preset_parts) >= 2:
                            data["preset"] = int(preset_parts[1])
                    except (ValueError, IndexError):
                        data["preset"] = None
            else:
                # Set defaults for powered off state
                data.update({
                    "volume_level": 0.0,
                    "muted": False,
                    "input": 1,
                    "preset": None,
                })

            return data

        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def send_command(self, command: str) -> str | None:
        """Send a command to the device."""
        result = await self.connection.send_command(command)
        # Trigger an immediate update after sending a command
        await self.async_request_refresh()
        return result

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        await self.connection.disconnect()


class StormAudioConnection:
    """Connection handler for StormAudio TCP/IP API."""
    
    def __init__(self, host: str, port: int):
        """Initialize the connection."""
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None
        self._lock = asyncio.Lock()

    async def connect(self) -> bool:
        """Connect to the StormAudio processor."""
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=TIMEOUT
            )
            _LOGGER.debug("Connected to StormAudio at %s:%s", self.host, self.port)
            return True
        except (OSError, asyncio.TimeoutError) as error:
            _LOGGER.error("Failed to connect to StormAudio: %s", error)
            return False

    async def disconnect(self):
        """Disconnect from the processor."""
        if self.writer:
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except Exception:
                pass
            self.writer = None
            self.reader = None

    async def send_command(self, command: str) -> str | None:
        """Send a command and return the response."""
        async with self._lock:
            if not self.writer:
                if not await self.connect():
                    return None

            try:
                # Send command with carriage return
                self.writer.write(f"{command}\r".encode())
                await self.writer.drain()
                
                # Read response
                response = await asyncio.wait_for(
                    self.reader.readuntil(b'\r'),
                    timeout=TIMEOUT
                )
                response_str = response.decode().strip()
                _LOGGER.debug("Sent: %s, Received: %s", command, response_str)
                return response_str
                
            except (OSError, asyncio.TimeoutError) as error:
                _LOGGER.error("Command failed: %s", error)
                await self.disconnect()
                return None