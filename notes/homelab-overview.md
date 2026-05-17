# Homelab Overview

Last verified: 2026-05-16 20:00 CDT

This repo is the canonical documentation home for the Proxmox home server. Use it as the first stop for understanding what exists, what should be running, and which files need updates when the server changes.

## Architecture

- Proxmox host: `proxmox`, repo path `/root/server-admin`.
- Home Assistant: VM `100`, LAN `192.168.1.187:8123`.
- AdGuard Home: CT `102`, LAN `192.168.1.189`.
- Stale Jellyfin candidate: CT `103`; do not rely on it unless explicitly asked.
- Active Jellyfin: CT `104`, LAN `192.168.1.191:8096`.
- Albumary: CT `105`, app directory `/opt/spotify_tracker`, SQLite database `/opt/spotify_tracker/data/spotify_tracker.sqlite`.
- Media stack: CT `106`, LAN `192.168.1.197`, Docker Compose host for Jellyseerr, Radarr, Sonarr, Prowlarr, qBittorrent, FileBrowser Quantum, Bazarr, FlareSolverr, and Gluetun.
- Remote access: CT `107`, LAN `192.168.1.198`, Tailscale subnet router for `192.168.1.0/24`.

Live state observed during the last verification:

- VM `100` was running.
- CT `103` was stopped.
- CTs `104`, `105`, `106`, and `107` were running.

## Storage And Paths

- Shared media host path: `/mnt/proxmox-usb-backup/media-stack`.
- CT `104` media mount: `/media`.
- CT `106` media mount: `/data`.
- Guest backup archives: `/mnt/proxmox-usb-backup/dump`.
- Host configuration backups: `/mnt/proxmox-usb-backup/host-config`.
- File-backup snapshots: `/mnt/proxmox-usb-backup/file-backups`.
- Albumary SQLite backups: `/mnt/proxmox-usb-backup/albumary-sqlite`.

See `notes/proxmox-media-inventory.md` for current guest, storage, mount, and service details. See `notes/media-stack-runbook.md` before changing Jellyfin, media services, Docker Compose, media storage, VPN routing, or FileBrowser.

## Access Model

- Services are LAN-only by default.
- Remote private access should use Tailscale through CT `107`.
- Do not expose Home Assistant, Jellyfin, qBittorrent, Radarr, Sonarr, Prowlarr, Jellyseerr, FileBrowser Quantum, Bazarr, or backup views publicly without a separate reverse-proxy/auth plan.
- Commercial outbound VPN routing is separate from Tailscale remote access and lives in CT `106` through Gluetun.

## Backups

- Proxmox guest backups target storage ID `usb-backup`.
- Host configuration backups are created by `homelab-host-backup.timer`.
- Host bind-mounted file backups are created by `homelab-file-backup.timer`.
- Albumary database-only backups are created by `albumary-sqlite-backup.timer`.
- Home Assistant should keep its own backup workflow enabled, including off-box sync.

See `notes/homelab-backup-runbook.md` for backup schedules, manual commands, restore notes, and safety boundaries.

## Dashboard And Service Catalog

`homelab-services.yml` is the machine-readable service catalog for dashboard-visible services and health checks. The Home Assistant package and Lovelace dashboard sources live under `home-assistant/` and are mirrored from that service catalog.

When a service owner, LAN IP, port, URL, health check, category, or dashboard visibility changes, update `homelab-services.yml` first, then update the generated or mirrored Home Assistant files and any affected runbook.

## Secret Boundary

Never commit real API keys, passwords, VPN credentials, Tailscale auth keys, provider credentials, app databases, or Proxmox private keys. This repo should document what secrets exist and where they belong, but not their values.

Use `notes/media-stack-credentials.md` and relevant `.example` files as pointer documentation.
