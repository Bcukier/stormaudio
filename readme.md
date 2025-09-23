# StormAudio Home Assistant Integration

A Home Assistant custom integration for controlling StormAudio Immersive Sound Processors via TCP/IP.

Works on StormAudio, Focal, and Bryston Audio

Note that this integration was 100% vibe coded using anthropic/claude and based on the protocols laid out in https://www.stormaudio.com/wp-content/uploads/2024/10/Stormaudio_isp_tcpip_api_protocol_fw4.6r1_v23.pdf

## Features

- **Full Media Player Control**
  - Power on/off with boot sequence detection
  - Volume control (slider and up/down buttons)
  - Mute/unmute
  - Input source selection
  - Real-time status updates

- **Automatic Network Discovery**
  - Scans local network for StormAudio devices during setup
  - Manual configuration option available

- **Enhanced Power-On Handling**
  - Automatic polling during device boot-up
  - Detects when processor is fully operational
  - Handles 30+ second boot sequences

- **External Change Detection**
  - 10-second polling interval for remote control changes
  - Manual refresh service available
  - Real-time status synchronization

## Supported Devices

This integration supports StormAudio Immersive Sound Processors running firmware 4.6r1 or later, including:

- StormAudio ISP series
- Focal Astral 16
- Bryston SP4
- Other StormAudio-based processors

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right and select "Custom repositories"
4. Add this repository URL and select "Integration" as the category
5. Click "Install"
6. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/stormaudio` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

### Via UI

1. Go to **Settings** → **Devices & Services** → **Integrations**
2. Click **"+ Add Integration"**
3. Search for **"StormAudio"**
4. Follow the setup wizard:
   - **Automatic Discovery**: Select your device from the list of discovered devices
   - **Manual Configuration**: Enter IP address, port (default: 23), and device name

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| Host | Required | IP address of your StormAudio device |
| Port | 23 | TCP port (Telnet) |
| Name | StormAudio | Friendly name for the device |

## Usage

### Media Player Controls

Once configured, the integration creates a media player entity with the following controls:

- **Power**: Turn device on/off
- **Volume**: Adjust volume level (-100dB to 0dB)
- **Mute**: Mute/unmute audio
- **Source**: Select input source (HDMI, Optical, AES, etc.)

### Services

#### `stormaudio.refresh_status`

Manually refresh the device status. Useful for immediately detecting external changes.

```yaml
service: stormaudio.refresh_status
```

### Automations

Example automation to refresh status when you suspect changes:

```yaml
automation:
  - alias: "Refresh StormAudio Status"
    trigger:
      - platform: state
        entity_id: remote.harmony_hub
        to: "on"
    action:
      - service: stormaudio.refresh_status
```

## Features in Detail

### Power-On Sequence Handling

When powering on the device:
1. Sends power-on command to StormAudio
2. Begins enhanced polling every 2 seconds
3. Monitors both power state and processor state
4. Continues until processor shows fully operational (state 2)
5. Automatically returns to normal 10-second polling

This ensures the UI correctly reflects the device state even during the 30+ second boot sequence.

### External Change Detection

The integration polls the device every 10 seconds to detect changes made via:
- Physical remote control
- Front panel controls
- Other control systems
- Mobile apps

For immediate updates, use the `stormaudio.refresh_status` service.

## Troubleshooting

### Integration shows "Unavailable"

**Check connection**: Ensure your StormAudio device is powered on and network accessible:
```bash
telnet [device_ip] 23
```

**Check IP address**: Verify the correct IP address is configured in the integration settings.

**Check firewall**: Ensure port 23 (Telnet) is not blocked between Home Assistant and StormAudio.

### Power status not updating

**Wait for boot sequence**: The device takes 30+ seconds to fully boot. The integration will automatically detect when ready.

**Manual refresh**: Use the `stormaudio.refresh_status` service to force an immediate status check.

**Check logs**: Enable debug logging to see status updates:
```yaml
logger:
  logs:
    custom_components.stormaudio: debug
```

### Volume level not showing

Ensure your Home Assistant version supports `MediaPlayerEntityFeature.VOLUME_SET`. The integration requires Home Assistant 2023.8 or later.

### Input selection not working

Verify your inputs are configured in the StormAudio device web interface. The integration automatically detects available inputs from the device.

## Debug Logging

To enable detailed debug logging:

```yaml
logger:
  logs:
    custom_components.stormaudio: debug
```

This will log:
- All commands sent to StormAudio
- All responses received
- Status parsing details
- Connection events
- Power-on sequence progress

## Technical Details

### Protocol

The integration uses the StormAudio TCP/IP API protocol:
- **Port**: 23 (Telnet)
- **Command format**: ASCII strings terminated with `\n` (LF)
- **Response format**: `ssp.parameter.[value]`

### Polling Behavior

- **Normal operation**: 10-second intervals
- **Power-on sequence**: 2-second intervals for up to 30 seconds
- **Manual refresh**: Immediate via service call

### Supported Commands

The integration implements the following StormAudio commands:
- `ssp.power.on/off` - Power control
- `ssp.vol.[value]` - Volume set
- `ssp.vol.up/down` - Volume adjust
- `ssp.mute.on/off` - Mute control
- `ssp.input.[value]` - Input selection
- `ssp.power` - Query power state
- `ssp.procstate` - Query processor state

## Known Limitations

- Input list is currently static (Apple TV, Video Game, HDMI 3). Future versions will dynamically parse from device.
- Preset selection not yet implemented
- Zone control not yet implemented
- Advanced audio settings (bass, treble, etc.) not yet exposed

## Credits

- Protocol documentation: [StormAudio TCP/IP API](https://www.stormaudio.com/wp-content/uploads/2024/10/Stormaudio_isp_tcpip_api_protocol_fw4.6r1_v23.pdf)
- Developed for Home Assistant community

## License

This integration is provided as-is for use with StormAudio devices.

## Support

For issues and feature requests, please use the GitHub issue tracker.

## Changelog

### Version 1.0.0
- Initial release
- Basic media player functionality
- Network discovery
- Power-on sequence handling
- External change detection
- Manual refresh service