# Proxmox Media Inventory

Last updated: 2026-05-06 20:20 CDT

## Host

- Hostname: `proxmox`
- CPU: Intel Core i5-10210U, 8 logical CPUs
- RAM: 7.5 GiB total
- Storage:
  - `local`: dir storage at `/var/lib/vz`, about 57 GiB free at inspection time
  - `local-lvm`: LVM-thin storage, about 124 GiB free at inspection time

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

## Service Ports

| Service | Port | URL | Purpose |
| --- | ---: | --- | --- |
| Jellyfin | 8096 | `http://192.168.1.191:8096` | Existing media server in CT 104 |
| Jellyseerr | 5055 | `http://192.168.1.197:5055` | Request/search UI |
| Radarr | 7878 | `http://192.168.1.197:7878` | Movie library management |
| Sonarr | 8989 | `http://192.168.1.197:8989` | TV library management |
| Prowlarr | 9696 | `http://192.168.1.197:9696` | Indexer manager |
| qBittorrent | 8080 | `http://192.168.1.197:8080` | Download client web UI |
| Bazarr | 6767 | `http://192.168.1.197:6767` | Subtitle management |

## Integration Status

- Radarr root folder configured: `/data/library/movies`
- Sonarr root folder configured: `/data/library/tv`
- qBittorrent configured as a download client in Radarr and Sonarr
- qBittorrent categories configured:
  - `radarr` -> `/data/downloads/complete/radarr`
  - `sonarr` -> `/data/downloads/complete/sonarr`
- Prowlarr configured with Radarr and Sonarr application sync
- Internet Archive configured as a public torrent indexer and synced to Radarr/Sonarr.
- Add only lawful/public-domain/owned-media sources.

## Policy

This stack is documented and configured for lawful/public-domain/owned-media workflows. Do not commit indexer, VPN, provider, or application API secrets to this repository.
