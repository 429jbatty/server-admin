# Proxmox Media Inventory

Last updated: 2026-06-07 17:18 CDT

## Host

- Active node: `pve-nuc`
- LAN address: `192.168.1.184/24`
- Hardware: Intel NUC10i7FNK
- CPU: Intel Core i7-10710U, 12 logical CPUs
- RAM: about 15 GiB total
- Retired source: Lenovo node `proxmox`, LAN `192.168.1.186`; all guests stopped and backup automation disabled
- Storage:
  - `local`: dir storage at `/var/lib/vz`, about 83 GiB free at inspection time
  - `local-lvm`: LVM-thin storage, about 316 GiB free at inspection time
  - `usb-backup`: dir storage at `/mnt/proxmox-usb-backup`, about 3.5 TiB free at inspection time, used for daily guest backups and live media storage
  - Live media stack path on HDD: `/mnt/proxmox-usb-backup/media-stack`
  - Backup folders on HDD:
    - `/mnt/proxmox-usb-backup/dump`
    - `/mnt/proxmox-usb-backup/file-backups`
    - `/mnt/proxmox-usb-backup/host-config`
- Resilience:
  - Proxmox `watchdog-mux` is active.
  - `/etc/default/pve-ha-manager` selects `WATCHDOG_MODULE=iTCO_wdt` so the
    Intel hardware watchdog is preferred on next startup.
  - Proxmox HA has no managed resources on this single-node host.

## Guests

| ID | Type | Name | Status | Notes |
| --- | --- | --- | --- | --- |
| 100 | VM | `homeassistant` | running | Home Assistant OS VM |
| 101 | LXC | `CT101` | stopped | Debian, static IP `192.168.1.50/24` |
| 102 | LXC | `adguard` | running | AdGuard community-script LXC |
| 103 | LXC | `jellyfin` | stopped | Stale candidate; Debian 12, `eth0` down, Jellyfin inactive |
| 104 | LXC | `jellyfin` | running | Active Jellyfin server |
| 105 | LXC | `CT105` | running | Debian, static IP `192.168.1.100/24` |
| 106 | LXC | `media-stack` | running | Docker Compose media automation stack, IP `192.168.1.197` |
| 107 | LXC | `remote-access` | running | Tailscale subnet-router target, IP `192.168.1.198`; authenticated, verify route approval from a remote client when troubleshooting |
| 108 | LXC | `monitoring` | running | Grafana, Prometheus, Uptime Kuma, and Proxmox exporter, IP `192.168.1.200` |

Startup order for active guests:

| Order | Guest | Delay After Start | Purpose |
| ---: | --- | ---: | --- |
| 10 | CT `102` AdGuard Home | 20s | Bring LAN DNS filtering up first. |
| 20 | VM `100` Home Assistant | 30s | Start core automation after DNS. |
| 30 | CT `104` Jellyfin | 20s | Start media serving after core services. |
| 40 | CT `105` Albumary | 15s | Start the app/database service. |
| 50 | CT `107` Tailscale subnet router | 15s | Restore private remote access. |
| 60 | CT `106` media stack | 45s | Give network and USB-backed media mounts time to settle. |
| 90 | CT `108` monitoring | 20s | Start observability last so it sees recovered services. |

## Active Jellyfin

- Container: CT `104`
- OS: Ubuntu 24.04
- Jellyfin: `10.11.8`
- URL: `http://192.168.1.191:8096`
- Service: `jellyfin.service`, enabled and active at inspection time
- Hardware devices configured:
  - `/dev/dri/renderD128`
  - `/dev/dri/card0`
- Root disk: 16 GiB on `local-lvm`
- Existing Jellyfin data was small at inspection time, about 1 MiB under `/var/lib/jellyfin`.

## Media Stack Target

- Container ID: CT `106`
- Hostname: `media-stack`
- URL base: `http://192.168.1.197`
- Purpose: Docker Compose host for Jellyseerr, Radarr, Sonarr, Prowlarr, qBittorrent, Bazarr, FileBrowser Quantum, and FlareSolverr
- Storage model: HDD host path at `/mnt/proxmox-usb-backup/media-stack`
- CT `104` mount target: `/media`
- CT `106` mount target: `/data`
- CT `106` backup browse mounts:
  - `/backups/guest-dumps` from `/mnt/proxmox-usb-backup/dump`, read-only
  - `/backups/media-library-current` from `/mnt/proxmox-usb-backup/file-backups/srv-media-stack/snapshots/20260603-015205/library`, read-only
- `/mnt/proxmox-usb-backup/media-stack` is the live media stack path. The host file-backup timer still snapshots it into `/mnt/proxmox-usb-backup/file-backups/srv-media-stack`; because this is the same physical HDD, those snapshots are useful for accidental-change rollback but are not a separate disk backup.
- `/dev/net/tun` passthrough configured for Gluetun.

## Remote Access Target

- Container ID: CT `107`
- Hostname: `remote-access`
- LAN IP: `192.168.1.198`
- Purpose: Tailscale subnet router for remote access to the home LAN.
- Advertised route: `192.168.1.0/24`
- `/dev/net/tun` passthrough configured.
- IP forwarding configured inside the container.
- Tailscale is authenticated with identity `100.103.90.53`; verify route approval from a remote client when troubleshooting.

## Monitoring Target

- Container ID: CT `108`
- Hostname: `monitoring`
- LAN IP: `192.168.1.200`
- Purpose: Grafana-based technical monitoring stack for Proxmox host health, storage trends, VM/LXC visibility, and service uptime.
- Runtime path: `/opt/monitoring`
- Repo source: `monitoring/`
- Services:
  - Grafana: `http://192.168.1.200:3000`
  - Prometheus: `http://192.168.1.200:9090`
  - Uptime Kuma: `http://192.168.1.200:3001`
  - Proxmox exporter: internal Docker service `pve-exporter:9221`
- Host `node_exporter` runs on the Proxmox host at `http://192.168.1.184:9100/metrics`.
- The Proxmox exporter uses a limited `PVEAuditor` API token stored only in CT `108` at `/opt/monitoring/secrets/pve.yml`.
- Prometheus scrapes Home Assistant's built-in exporter at `http://192.168.1.187:8123/api/prometheus` using a long-lived Home Assistant token stored only in CT `108` at `/opt/monitoring/secrets/home-assistant-prometheus-token`.
- Prometheus scrapes internal Albumary website monitoring targets in CT `108`: `albumary-cloudflare-exporter:9210` for Cloudflare analytics and `blackbox-exporter:9115` for public HTTPS probing.

## Service Ports

| Service | Port | URL | Purpose |
| --- | ---: | --- | --- |
| Home Assistant | 8123 | `http://192.168.1.187:8123` | Home automation dashboard |
| Home Assistant Prometheus | 8123 | `http://192.168.1.187:8123/api/prometheus` | Token-protected Home Assistant sensor metrics for Grafana |
| Proxmox Metrics Exporter | 9108 | `http://192.168.1.184:9108/metrics/homelab` | LAN-only host/guest resource metrics for Home Assistant |
| Proxmox node_exporter | 9100 | `http://192.168.1.184:9100/metrics` | LAN-only Prometheus host metrics for Grafana |
| AdGuard Home | 80 | `http://192.168.1.189` | LAN DNS filtering |
| Jellyfin | 8096 | `http://192.168.1.191:8096` | Existing media server in CT 104 |
| Jellyseerr | 5055 | `http://192.168.1.197:5055` | Request/search UI |
| Radarr | 7878 | `http://192.168.1.197:7878` | Movie library management |
| Sonarr | 8989 | `http://192.168.1.197:8989` | TV library management |
| Prowlarr | 9696 | `http://192.168.1.197:9696` | Indexer manager |
| qBittorrent | 8080 | `http://192.168.1.197:8080` | Download client web UI |
| FileBrowser Quantum | 8090 | `http://192.168.1.197:8090` | LAN-only media file browser and admin-only backup browser |
| Bazarr | 6767 | `http://192.168.1.197:6767` | Subtitle management |
| Grafana | 3000 | `http://192.168.1.200:3000` | Technical monitoring dashboard |
| Prometheus | 9090 | `http://192.168.1.200:9090` | Metrics collection and query engine |
| Uptime Kuma | 3001 | `http://192.168.1.200:3001` | Service uptime monitors |
| Albumary Cloudflare Exporter | 9210 | Internal Docker service only | Cloudflare HTTP and Web Analytics metrics for Grafana |
| Blackbox Exporter | 9115 | Internal Docker service only | Public HTTPS probe metrics for Grafana |

After outbound VPN activation, Gluetun publishes the qBittorrent and Prowlarr Web UIs because both containers share Gluetun's network namespace. FlareSolverr also shares Gluetun's network namespace for Prowlarr-only indexer challenge handling, but it does not publish a LAN port. Radarr, Sonarr, Jellyseerr, Bazarr, and CT `104` Jellyfin keep their normal Docker/LAN network path.

The repo-level source of truth for the Home Assistant Homelab dashboard is `homelab-services.yml`. The installed Home Assistant package and dashboard YAML are mirrored from `home-assistant/`.

## Integration Status

- Radarr root folder configured: `/data/library/movies`
- Sonarr root folder configured: `/data/library/tv`
- qBittorrent configured as a download client in Radarr and Sonarr
- qBittorrent categories configured:
  - `radarr` -> `/data/downloads/complete/radarr`
  - `sonarr` -> `/data/downloads/complete/sonarr`
- qBittorrent has no global download or upload speed limits. CT `106` retains
  its 2-core and 2 GiB RAM resource limits.
- Prowlarr configured with Radarr and Sonarr application sync
- Internet Archive configured as a public torrent indexer and synced to Radarr/Sonarr.
- 1337x configured as a public torrent indexer in Prowlarr with a tagged FlareSolverr proxy, then synced to Radarr/Sonarr as `1337x (Prowlarr)`.
- TorrentGalaxy, The Pirate Bay, and LimeTorrents configured as public torrent indexers in Prowlarr, then synced to Radarr/Sonarr as Prowlarr-backed Torznab indexers.
- FileBrowser Quantum configured in CT `106` with the media library writable through the admin account, a read-only viewer account for the media library, and admin-only read-only backup sources. Host-config backups are intentionally excluded.
- The FileBrowser media-library backup mount uses the resolved latest snapshot path because Proxmox does not hotplug bind mounts through the `current` symlink. Refresh this mount after a newer snapshot should be browsed.
- Outbound VPN Compose routes qBittorrent, Prowlarr, and FlareSolverr through Gluetun.
- Home Assistant Homelab metrics track HDD total usage plus grouped Media and Backups folder usage.
- Grafana Home Assistant metrics track the focused Prometheus export set from `home-assistant/prometheus_package.yaml`: comfort sensors, batteries, selected presence/security binary sensors, lights/switches, and chore/status helpers.
- Add only lawful/public-domain/owned-media sources.

## Policy

This stack is documented and configured for lawful/public-domain/owned-media workflows. Do not commit indexer, VPN, provider, or application API secrets to this repository.
