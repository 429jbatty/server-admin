# Proxmox Media Inventory

Last updated: 2026-05-11 23:38 CDT

## Host

- Hostname: `proxmox`
- CPU: Intel Core i5-10210U, 8 logical CPUs
- RAM: 7.5 GiB total
- Storage:
  - `local`: dir storage at `/var/lib/vz`, about 57 GiB free at inspection time
  - `local-lvm`: LVM-thin storage, about 124 GiB free at inspection time
  - `usb-backup`: dir storage at `/mnt/proxmox-usb-backup`, about 3.6 TiB free at setup time, used for daily guest backups

## Guests

| ID | Type | Name | Status | Notes |
| --- | --- | --- | --- | --- |
| 100 | VM | `homeassistant` | running | Home Assistant OS VM |
| 101 | LXC | `CT101` | stopped | Debian, static IP `192.168.1.50/24` |
| 102 | LXC | `adguard` | running | AdGuard community-script LXC |
| 103 | LXC | `jellyfin` | running | Stale candidate; Debian 12, `eth0` down, Jellyfin inactive |
| 104 | LXC | `jellyfin` | running | Active Jellyfin server |
| 105 | LXC | `CT105` | running | Debian, static IP `192.168.1.100/24` |
| 106 | LXC | `media-stack` | running | Docker Compose media automation stack, IP `192.168.1.197` |
| 107 | LXC | `remote-access` | running | Tailscale subnet-router target, IP `192.168.1.198`; awaiting account auth/route approval |

## Active Jellyfin

- Container: CT `104`
- OS: Ubuntu 24.04
- Jellyfin: `10.11.8`
- URL: `http://192.168.1.191:8096`
- Service: `jellyfin.service`, enabled and active at inspection time
- Hardware devices configured:
  - `/dev/dri/renderD128`
  - `/dev/dri/card1`
- Root disk: 16 GiB on `local-lvm`
- Existing Jellyfin data was small at inspection time, about 1 MiB under `/var/lib/jellyfin`.

## Media Stack Target

- Container ID: CT `106`
- Hostname: `media-stack`
- URL base: `http://192.168.1.197`
- Purpose: Docker Compose host for Jellyseerr, Radarr, Sonarr, Prowlarr, qBittorrent, and Bazarr
- Storage model: temporary local host path at `/srv/media-stack`
- CT `104` mount target: `/media`
- CT `106` mount target: `/data`
- `/srv/media-stack` is backed up by the host file-backup timer because Proxmox excludes host bind mounts from CT archives.
- `/dev/net/tun` passthrough configured for Gluetun.

## Remote Access Target

- Container ID: CT `107`
- Hostname: `remote-access`
- LAN IP: `192.168.1.198`
- Purpose: Tailscale subnet router for remote access to the home LAN.
- Advertised route: `192.168.1.0/24`
- `/dev/net/tun` passthrough configured.
- IP forwarding configured inside the container.
- Tailscale installed; account authentication and route approval must be completed in Tailscale.

## Service Ports

| Service | Port | URL | Purpose |
| --- | ---: | --- | --- |
| Home Assistant | 8123 | `http://192.168.1.187:8123` | Home automation dashboard |
| Proxmox Metrics Exporter | 9108 | `http://192.168.1.184:9108/metrics/homelab` | LAN-only host/guest resource metrics for Home Assistant |
| AdGuard Home | 80 | `http://192.168.1.189` | LAN DNS filtering |
| Jellyfin | 8096 | `http://192.168.1.191:8096` | Existing media server in CT 104 |
| Jellyseerr | 5055 | `http://192.168.1.197:5055` | Request/search UI |
| Radarr | 7878 | `http://192.168.1.197:7878` | Movie library management |
| Sonarr | 8989 | `http://192.168.1.197:8989` | TV library management |
| Prowlarr | 9696 | `http://192.168.1.197:9696` | Indexer manager |
| qBittorrent | 8080 | `http://192.168.1.197:8080` | Download client web UI |
| Bazarr | 6767 | `http://192.168.1.197:6767` | Subtitle management |

After outbound VPN activation, Gluetun publishes the qBittorrent and Prowlarr Web UIs because both containers share Gluetun's network namespace. Radarr, Sonarr, Jellyseerr, Bazarr, and CT `104` Jellyfin keep their normal Docker/LAN network path.

The repo-level source of truth for the Home Assistant Homelab dashboard is `homelab-services.yml`. The installed Home Assistant package and dashboard YAML are mirrored from `home-assistant/`.

## Integration Status

- Radarr root folder configured: `/data/library/movies`
- Sonarr root folder configured: `/data/library/tv`
- qBittorrent configured as a download client in Radarr and Sonarr
- qBittorrent categories configured:
  - `radarr` -> `/data/downloads/complete/radarr`
  - `sonarr` -> `/data/downloads/complete/sonarr`
- Prowlarr configured with Radarr and Sonarr application sync
- Internet Archive configured as a public torrent indexer and synced to Radarr/Sonarr.
- Outbound VPN Compose changes route qBittorrent and Prowlarr through Gluetun. Do not apply the updated Compose file in CT `106` until `/opt/media-stack/vpn.env` contains real Proton WireGuard values.
- Add only lawful/public-domain/owned-media sources.

## Policy

This stack is documented and configured for lawful/public-domain/owned-media workflows. Do not commit indexer, VPN, provider, or application API secrets to this repository.
