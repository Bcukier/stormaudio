from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.components.media_player.const import (
    SUPPORT_VOLUME_SET, SUPPORT_VOLUME_STEP, SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON, SUPPORT_SELECT_SOURCE
)

class StormAudioMediaPlayer(MediaPlayerEntity):
    def __init__(self, client):
        self._client = client
        self._state = None
        self._volume = None
        self._source = None

    def update(self):
        self._state = self._client.send_command("POW=?")
        self._volume = self._client.send_command("VOL=?")
        self._source = self._client.send_command("INP=?")

    def turn_on(self):
        self._client.send_command("POWON")

    def turn_off(self):
        self._client.send_command("POWOFF")

    def volume_up(self):
        self._client.send_command("VOLUP")

    def volume_down(self):
        self._client.send_command("VOLDN")

    def set_volume_level(self, volume):
        # Normalize 0.0 - 1.0 to dB level (API expects -79 to 12)
        db_volume = int(volume * 91 - 79)
        self._client.send_command(f"VOL={db_volume}")

    def select_source(self, source):
        self._client.send_command(f"INP={source}")
