### File: custom_components/stormaudio/__init__.py

DOMAIN = "stormaudio"

async def async_setup(hass, config):
    return True

async def async_setup_entry(hass, entry):
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "media_player")
    )
    return True

async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_forward_entry_unload(entry, "media_player")


### File: custom_components/stormaudio/manifest.json

{
  "domain": "stormaudio",
  "name": "StormAudio Amplifier",
  "version": "1.0",
  "requirements": [],
  "dependencies": [],
  "codeowners": ["@yourgithub"]
}


### File: custom_components/stormaudio/media_player.py

import logging
import socket

from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.components.media_player.const import (
    SUPPORT_VOLUME_SET, SUPPORT_VOLUME_STEP, SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON, SUPPORT_SELECT_SOURCE
)
from homeassistant.const import STATE_OFF, STATE_ON

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = (
    SUPPORT_TURN_ON | SUPPORT_TURN_OFF | SUPPORT_VOLUME_STEP |
    SUPPORT_VOLUME_SET | SUPPORT_SELECT_SOURCE
)

class StormAudioClient:
    def __init__(self, host, port=23, timeout=2):
        self.host = host
        self.port = port
        self.timeout = timeout

    def send_command(self, command):
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                sock.sendall(f"{command}\r".encode())
                response = sock.recv(1024)
                return response.decode().strip()
        except Exception as e:
            _LOGGER.error("Error sending command '%s': %s", command, e)
            return None

class StormAudioMediaPlayer(MediaPlayerEntity):
    def __init__(self, name, host):
        self._name = name
        self._client = StormAudioClient(host)
        self._state = STATE_OFF
        self._volume = 0
        self._source = None

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def volume_level(self):
        return self._volume

    @property
    def source(self):
        return self._source

    @property
    def supported_features(self):
        return SUPPORT_FLAGS

    def update(self):
        pow_state = self._client.send_command("POW=?")
        self._state = STATE_ON if pow_state == "POWON" else STATE_OFF

        vol = self._client.send_command("VOL=?")
        try:
            self._volume = (int(vol.split("=")[1]) + 79) / 91
        except:
            pass

        inp = self._client.send_command("INP=?")
        self._source = inp.split("=")[1] if "=" in inp else inp

    def turn_on(self):
        self._client.send_command("POWON")

    def turn_off(self):
        self._client.send_command("POWOFF")

    def volume_up(self):
        self._client.send_command("VOLUP")

    def volume_down(self):
        self._client.send_command("VOLDN")

    def set_volume_level(self, volume):
        db_volume = int(volume * 91 - 79)
        self._client.send_command(f"VOL={db_volume}")

    def select_source(self, source):
        self._client.send_command(f"INP={source}")


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    async_add_entities([StormAudioMediaPlayer("StormAudio Amp", config["host"])])


### Example configuration.yaml (outside the integration but needed)

# media_player:
#   - platform: stormaudio
#     host: 192.168.1.100
