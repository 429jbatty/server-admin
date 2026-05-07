# HarmHo Script - Harmen Hoek Playlist Launcher

## What It Does
Turns on your home theater setup and launches a random Harmen Hoek video from the YouTube playlist on your Roku.

## Components
- **Remote/TV**: Turns on (Home Theater)
- **Denon Receiver**: Selects "Princess Jelly" source
- **Roku**: Selects YouTube app, then launches the playlist

## How to Add This to Home Assistant

The script below uses two methods:

### Method 1: Simple (Recommended for Roku)
Uses Roku's ECP API to directly launch the YouTube playlist.

### Method 2: Shell Command
Uses curl to hit the Roku's API endpoint.

---

## Your Updated Script YAML

Copy and paste this into **Settings → Automations & Scenes → Scripts → Create Script** (or edit the HarmHo script):

```yaml
sequence:
  - type: turn_on
    device_id: cb43f2cbd6e7a07bea951d312629d416
    entity_id: fa416a0cfd4511f47da9e0f8bf5635f8
    domain: remote
  - action: media_player.select_source
    metadata: {}
    target:
      entity_id: media_player.home_theater_2
    data:
      source: Princess Jelly
  - action: media_player.select_source
    metadata: {}
    target:
      entity_id: media_player.princess_jellybean
    data:
      source: YouTube
  - action: shell_command.roku_launch_playlist
    metadata: {}
alias: HarmHo
description: ""
```

---

## Add Shell Command to Configuration

1. Go to **Settings → Devices & Services → YAML**
2. Edit your `configuration.yaml` file and add this section:

```yaml
shell_command:
  roku_launch_playlist: 'curl -X POST "http://192.168.1.156:8060/launch/837?url=https%3A%2F%2Fwww.youtube.com%2Fplaylist%3Flist%3DPL5oVF2z3WgsQ3RFDiIsBMnIuF9WPvHkFr"'
```

3. Restart Home Assistant (or reload YAML)

---

## How It Works

- **837** = YouTube channel ID on Roku
- **URL** = Your encoded playlist URL
- The Roku receives the request and opens YouTube with the playlist
- YouTube automatically plays a random video from the playlist

---

## Testing

Once added, you can test by:
1. Go to **Settings → Developer Tools → Services**
2. Search for `shell_command.roku_launch_playlist`
3. Click **Call Service**
4. Your Roku should launch the playlist!

---

## Troubleshooting

### Roku doesn't respond
- Check if 192.168.1.156 is still the correct IP (IPs can change)
- Verify Roku is on the same network as Proxmox host
- Try: `curl -v http://192.168.1.156:8060/query/device-info` to test connectivity

### Playlist doesn't launch
- YouTube app might need to be manually opened first
- Try selecting YouTube source again before running script

### Firewall blocks request
- If running, check iptables or Proxmox firewall rules
- Roku ECP uses port 8060

---

## Future Enhancements

- Add delay between steps (give Denon time to switch inputs)
- Add volume control
- Add conditional logic (only run if Roku is on)
- Add notification when playlist starts

---

## Device IDs Reference
- Remote: cb43f2cbd6e7a07bea951d312629d416
- Denon Receiver: media_player.home_theater_2
- Roku: media_player.princess_jellybean
- Roku IP: 192.168.1.156
- Playlist: https://www.youtube.com/playlist?list=PL5oVF2z3WgsQ3RFDiIsBMnIuF9WPvHkFr
