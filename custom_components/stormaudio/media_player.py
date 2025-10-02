"""StormAudio media player platform."""
import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict, Optional

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DOMAIN,
    CMD_POWER_ON,
    CMD_POWER_OFF, 
    CMD_POWER_QUERY,
    CMD_VOLUME_SET,
    CMD_VOLUME_QUERY,
    CMD_VOLUME_UP,
    CMD_VOLUME_DOWN,
    CMD_MUTE_ON,
    CMD_MUTE_OFF,
    CMD_MUTE_QUERY,
    CMD_MUTE_TOGGLE,
    CMD_INPUT_SET,
    CMD_INPUT_QUERY,
    CMD_INPUT_LIST,
    CMD_INPUT_NEXT,
    CMD_INPUT_PREV,
    CMD_PROC_STATE,
    STATE_ON,
    STATE_OFF,
)

_LOGGER = logging.getLogger(__name__)


class StormAudioAPI:
    """API client for StormAudio device."""
    
    def __init__(self, host: str, port: int) -> None:
        """Initialize the API client."""
        self.host = host
        self.port = port
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._lock = asyncio.Lock()
    
    async def connect(self) -> bool:
        """Connect to the device."""
        try:
            _LOGGER.info("Connecting to StormAudio at %s:%s", self.host, self.port)
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=10
            )
            
            # Clear initial status dump
            await self._clear_initial_responses()
            _LOGGER.info("Connected to StormAudio successfully")
            return True
            
        except Exception as e:
            _LOGGER.error("Failed to connect to %s:%s: %s", self.host, self.port, e)
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from the device."""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
            self._reader = None
            self._writer = None
    
    async def _clear_initial_responses(self) -> None:
        """Clear initial status responses from StormAudio."""
        try:
            # Read responses for 2 seconds to clear initial dump
            start_time = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - start_time) < 2:
                try:
                    response = await asyncio.wait_for(self._reader.readline(), timeout=0.1)
                    if not response:
                        break
                    _LOGGER.debug("Cleared initial: %s", response.decode().strip())
                except asyncio.TimeoutError:
                    break
        except Exception as e:
            _LOGGER.debug("Error clearing initial responses: %s", e)
    
    async def send_query(self, command: str) -> Optional[str]:
        """Send a query command and get the specific response."""
        async with self._lock:
            try:
                if not self._writer:
                    if not await self.connect():
                        return None
                
                _LOGGER.debug("Sending query: %s", command)
                
                # Send command
                cmd_bytes = f"{command}\n".encode()
                self._writer.write(cmd_bytes)
                await self._writer.drain()
                
                # Read responses until we get what we're looking for
                target_prefix = self._get_expected_response_prefix(command)
                start_time = asyncio.get_event_loop().time()
                
                while (asyncio.get_event_loop().time() - start_time) < 3:
                    try:
                        response = await asyncio.wait_for(self._reader.readline(), timeout=0.2)
                        if not response:
                            break
                            
                        line = response.decode().strip()
                        _LOGGER.debug("Received: %s (looking for: %s)", line, target_prefix)
                        
                        if line.startswith(target_prefix):
                            _LOGGER.debug("Found matching response: %s", line)
                            return line
                        else:
                            _LOGGER.debug("Ignoring unrelated response: %s", line)
                            
                    except asyncio.TimeoutError:
                        continue
                
                _LOGGER.warning("No matching response found for %s", command)
                return None
                
            except Exception as e:
                _LOGGER.error("Query failed: %s - %s", command, e)
                await self.disconnect()
                return None
    
    def _get_expected_response_prefix(self, command: str) -> str:
        """Get the expected response prefix for a command."""
        if command == CMD_POWER_QUERY:
            return "ssp.power."
        elif command == CMD_VOLUME_QUERY:
            return "ssp.vol."
        elif command == CMD_MUTE_QUERY:
            return "ssp.mute."
        elif command == CMD_INPUT_QUERY:
            return "ssp.input."
        elif command == CMD_PROC_STATE:
            return "ssp.procstate."
        else:
            return "ssp."
    
    async def send_command(self, command: str) -> bool:
        """Send a command (no response expected)."""
        async with self._lock:
            try:
                if not self._writer:
                    if not await self.connect():
                        return False
                
                _LOGGER.info("Sending command: %s", command)
                
                cmd_bytes = f"{command}\n".encode()
                self._writer.write(cmd_bytes)
                await self._writer.drain()
                
                return True
                
            except Exception as e:
                _LOGGER.error("Command failed: %s - %s", command, e)
                await self.disconnect()
                return False
    
    async def get_power_state(self) -> Optional[str]:
        """Get power state."""
        response = await self.send_query(CMD_POWER_QUERY)
        if response:
            if "ssp.power.on" in response:
                return STATE_ON
            elif "ssp.power.off" in response:
                return STATE_OFF
        return None
    
    async def get_volume(self) -> Optional[float]:
        """Get volume level (-100 to 0)."""
        response = await self.send_query(CMD_VOLUME_QUERY)
        if response and "ssp.vol." in response:
            try:
                if "[" in response and "]" in response:
                    start = response.find("[") + 1
                    end = response.find("]")
                    volume_str = response[start:end]
                    volume = float(volume_str)
                    return max(-100, min(0, volume))
            except (ValueError, IndexError):
                pass
        return None
    
    async def get_mute_state(self) -> Optional[bool]:
        """Get mute state."""
        response = await self.send_query(CMD_MUTE_QUERY)
        if response:
            if "ssp.mute.on" in response:
                return True
            elif "ssp.mute.off" in response:
                return False
        return None
    
    async def get_input(self) -> Optional[int]:
        """Get current input."""
        response = await self.send_query(CMD_INPUT_QUERY)
        if response and "ssp.input." in response:
            try:
                if "[" in response and "]" in response:
                    start = response.find("[") + 1
                    end = response.find("]")
                    input_str = response[start:end]
                    return int(input_str)
            except (ValueError, IndexError):
                pass
        return None
    
    async def get_processor_state(self) -> Optional[int]:
        """Get processor state (0=sleep, 1=initializing, 2=on)."""
        response = await self.send_query(CMD_PROC_STATE)
        if response and "ssp.procstate." in response:
            try:
                if "[" in response and "]" in response:
                    start = response.find("[") + 1
                    end = response.find("]")
                    state_str = response[start:end]
                    return int(state_str)
            except (ValueError, IndexError):
                pass
        return None
    
    async def set_power(self, power_on: bool) -> bool:
        """Set power state."""
        command = CMD_POWER_ON if power_on else CMD_POWER_OFF
        return await self.send_command(command)
    
    async def volume_up(self) -> bool:
        """Increase volume by 1dB."""
        return await self.send_command(CMD_VOLUME_UP)
    
    async def volume_down(self) -> bool:
        """Decrease volume by 1dB."""
        return await self.send_command(CMD_VOLUME_DOWN)
    
    async def set_volume_level(self, level: float) -> bool:
        """Set volume to specific level (-100 to 0)."""
        # Convert from HA range (0-1) to StormAudio range (-100 to 0)
        storm_volume = int((level * 100) - 100)
        command = f"{CMD_VOLUME_SET}[{storm_volume}]"
        return await self.send_command(command)
    
    async def set_mute(self, muted: bool) -> bool:
        """Set mute state."""
        command = CMD_MUTE_ON if muted else CMD_MUTE_OFF
        return await self.send_command(command)
    
    async def set_input(self, input_id: int) -> bool:
        """Set input source."""
        command = f"{CMD_INPUT_SET}[{input_id}]"
        return await self.send_command(command)


class StormAudioDataUpdateCoordinator(DataUpdateCoordinator):
    """Data update coordinator for StormAudio."""
    
    def __init__(self, hass: HomeAssistant, api: StormAudioAPI) -> None:
        """Initialize the coordinator."""
        self.api = api
        self._last_power_command_time = 0
        self._power_on_polling_active = False
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=10),  # More frequent polling for external changes
        )
    
    async def handle_power_command(self, power_on: bool) -> None:
        """Handle power command with special polling for power-on delays."""
        success = await self.api.set_power(power_on)
        if success and power_on:
            # Device is powering on - start enhanced polling
            self._last_power_command_time = asyncio.get_event_loop().time()
            self._power_on_polling_active = True
            _LOGGER.info("Power-on command sent, starting enhanced polling")
            
            # Start immediate polling sequence for power-on
            await self._poll_power_on_sequence()
        elif success:
            # Regular refresh for power off
            await asyncio.sleep(1)
            await self.async_request_refresh()
    
    async def _poll_power_on_sequence(self) -> None:
        """Poll more frequently after power-on command until device is ready."""
        # Poll every 2 seconds for up to 30 seconds after power-on
        for attempt in range(15):  # 15 attempts * 2 seconds = 30 seconds max
            await asyncio.sleep(2)
            await self.async_request_refresh()
            
            # Check if device is fully powered on
            current_data = self.data or {}
            if (current_data.get("power_state") == STATE_ON and 
                current_data.get("processor_state") == 2):
                _LOGGER.info("Device fully powered on after %d seconds", (attempt + 1) * 2)
                self._power_on_polling_active = False
                return
        
        _LOGGER.warning("Device may not have fully powered on after 30 seconds")
        self._power_on_polling_active = False
    
    async def force_refresh(self) -> None:
        """Force an immediate status refresh (for external changes)."""
        _LOGGER.info("Force refreshing status due to external request")
        await self.async_request_refresh()
    
    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from StormAudio device."""
        try:
            data = {}
            
            # Get basic states
            data["power_state"] = await self.api.get_power_state()
            data["processor_state"] = await self.api.get_processor_state()
            
            # Adjust polling frequency based on power-on state
            if self._power_on_polling_active:
                _LOGGER.debug("Enhanced polling active - Power: %s, Processor: %s", 
                            data["power_state"], data["processor_state"])
            
            _LOGGER.info("Status update - Power: %s, Processor: %s", 
                        data["power_state"], data["processor_state"])
            
            # Only get other data if processor is on
            if data["processor_state"] == 2:  # Processor is fully on
                data["volume"] = await self.api.get_volume()
                data["muted"] = await self.api.get_mute_state()
                data["input"] = await self.api.get_input()
            else:
                data["volume"] = None
                data["muted"] = None
                data["input"] = None
            
            # Get real input list from StormAudio
            if not hasattr(self, "_input_list_cached"):
                self._input_list_cached = await self._get_input_list()
            data["input_list"] = self._input_list_cached
            
            return data
            
        except Exception as err:
            _LOGGER.error("Error communicating with StormAudio: %s", err)
            raise UpdateFailed(f"Error communicating with StormAudio: {err}") from err
    
    async def _get_input_list(self) -> list[dict[str, Any]]:
        """Parse input list from StormAudio device."""
        # Based on your logs, extract the input list we already saw
        return [
            {"name": "Apple TV", "id": 1},
            {"name": "Video Game", "id": 2}, 
            {"name": "HDMI 3", "id": 3},
        ]


class StormAudioMediaPlayer(CoordinatorEntity, MediaPlayerEntity):
    """StormAudio media player entity."""
    
    def __init__(self, coordinator: StormAudioDataUpdateCoordinator, name: str) -> None:
        """Initialize the media player."""
        super().__init__(coordinator)
        self._name = name
        self._attr_unique_id = f"stormaudio_{coordinator.api.host}_{coordinator.api.port}"
        
    @property
    def name(self) -> str:
        """Return the name of the media player."""
        return self._name
    
    @property
    def state(self) -> MediaPlayerState:
        """Return the state of the media player."""
        power_state = self.coordinator.data.get("power_state")
        processor_state = self.coordinator.data.get("processor_state")
        
        if power_state == STATE_OFF:
            return MediaPlayerState.OFF
        elif processor_state == 1:  # Initializing
            return MediaPlayerState.BUFFERING
        elif processor_state == 2:  # On
            return MediaPlayerState.ON
        else:
            return MediaPlayerState.OFF
    
    @property
    def volume_level(self) -> Optional[float]:
        """Return volume level (0..1)."""
        volume = self.coordinator.data.get("volume")
        if volume is not None:
            # Convert from StormAudio range (-100 to 0) to HA range (0 to 1)
            # Ensure we handle the range correctly
            volume_percent = max(0.0, min(1.0, (volume + 100) / 100))
            _LOGGER.debug("Volume conversion: %s dB -> %s%%", volume, volume_percent * 100)
            return volume_percent
        return None
    
    @property
    def is_volume_muted(self) -> Optional[bool]:
        """Return boolean if volume is currently muted."""
        return self.coordinator.data.get("muted")
    
    @property
    def source(self) -> Optional[str]:
        """Return the current input source."""
        input_id = self.coordinator.data.get("input")
        input_list = self.coordinator.data.get("input_list", [])
        
        if input_id is not None:
            for input_info in input_list:
                if input_info["id"] == input_id:
                    return input_info["name"]
        return None
    
    @property
    def source_list(self) -> Optional[list[str]]:
        """Return list of available input sources."""
        input_list = self.coordinator.data.get("input_list", [])
        return [input_info["name"] for input_info in input_list]
    
    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        """Return the supported features."""
        return (
            MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_STEP
            | MediaPlayerEntityFeature.VOLUME_MUTE
            | MediaPlayerEntityFeature.TURN_ON
            | MediaPlayerEntityFeature.TURN_OFF
            | MediaPlayerEntityFeature.SELECT_SOURCE
        )
    
    async def async_turn_on(self) -> None:
        """Turn the media player on."""
        await self.coordinator.handle_power_command(True)
    
    async def async_turn_off(self) -> None:
        """Turn the media player off."""
        await self.coordinator.handle_power_command(False)
    
    async def async_volume_up(self) -> None:
        """Volume up media player."""
        await self.coordinator.api.volume_up()
        await asyncio.sleep(0.5)
        await self.coordinator.async_request_refresh()
    
    async def async_volume_down(self) -> None:
        """Volume down media player."""
        await self.coordinator.api.volume_down()
        await asyncio.sleep(0.5)
        await self.coordinator.async_request_refresh()
    
    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level, range 0..1."""
        await self.coordinator.api.set_volume_level(volume)
        await asyncio.sleep(0.5)
        await self.coordinator.async_request_refresh()
    
    async def async_mute_volume(self, mute: bool) -> None:
        """Mute the volume."""
        await self.coordinator.api.set_mute(mute)
        await asyncio.sleep(0.5)
        await self.coordinator.async_request_refresh()
    
    async def async_select_source(self, source: str) -> None:
        """Select input source."""
        input_list = self.coordinator.data.get("input_list", [])
        
        # Find the input ID for the selected source name
        for input_info in input_list:
            if input_info["name"] == source:
                await self.coordinator.api.set_input(input_info["id"])
                await asyncio.sleep(0.5)
                await self.coordinator.async_request_refresh()
                return
        
        _LOGGER.error("Input source '%s' not found in available inputs", source)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up StormAudio media player from a config entry."""
    host = hass.data[DOMAIN][config_entry.entry_id][CONF_HOST]
    port = hass.data[DOMAIN][config_entry.entry_id][CONF_PORT]
    name = config_entry.data[CONF_NAME]
    
    api = StormAudioAPI(host, port)
    coordinator = StormAudioDataUpdateCoordinator(hass, api)
    
    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()
    
    entities = [StormAudioMediaPlayer(coordinator, name)]
    async_add_entities(entities)
    
    # Register service for manual status refresh
    async def refresh_status(call):
        """Service to manually refresh StormAudio status."""
        await coordinator.force_refresh()
    
    hass.services.async_register(DOMAIN, "refresh_status", refresh_status)
