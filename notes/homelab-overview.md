# Homelab Overview

Last verified: 2026-06-14 11:12 CDT

This repo is the canonical documentation home for the Proxmox home server. Use it as the first stop for understanding what exists, what should be running, and which files need updates when the server changes.

## Architecture

- Active Proxmox host: Intel NUC node `pve-nuc`, LAN `192.168.1.184`, repo path `/root/server-admin`.
- Retired migration source: Lenovo node `proxmox`, LAN `192.168.1.186`; all guests are stopped and backup automation is disabled.
- Home Assistant: VM `100`, LAN `192.168.1.187:8123`.
- AdGuard Home: CT `102`, LAN `192.168.1.189`.
- Stale Jellyfin candidate: CT `103`; do not rely on it unless explicitly asked.
- Active Jellyfin: CT `104`, LAN `192.168.1.191:8096`.
- Albumary: CT `105`, app directory `/opt/spotify_tracker`, SQLite database `/opt/spotify_tracker/data/spotify_tracker.sqlite`.
- Media stack: CT `106`, LAN `192.168.1.197`, Docker Compose host for Jellyseerr, Radarr, Sonarr, Prowlarr, qBittorrent, FileBrowser Quantum, Bazarr, FlareSolverr, and Gluetun.
- Remote access: CT `107`, LAN `192.168.1.198`, Tailscale subnet router for `192.168.1.0/24`.
- Monitoring: CT `108`, LAN `192.168.1.200`, Docker Compose host for Grafana, Prometheus, Uptime Kuma, and the Proxmox exporter.

Live state observed during the last verification:

- VM `100` is running.
- CTs `102`, `104`, `105`, `106`, `107`, and `108` are running.
- Reference CT `101` and stale CT `103` are stopped.
- Active guests have `onboot: 1` with explicit startup ordering for reboot
  recovery: CT `102`, VM `100`, CT `104`, CT `105`, CT `107`, CT `106`, then
  CT `108`.
- Proxmox `watchdog-mux` is active and configured to load `wdat_wdt` from
  `/etc/default/pve-ha-manager` on next startup. Current HA resource list is
  empty; this host is not configured for multi-node HA failover.

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

Grafana is the technical monitoring dashboard and lives outside the Home Assistant control dashboard. See `notes/monitoring-runbook.md` for the monitoring stack, Prometheus scrape targets, Grafana dashboard source, and Uptime Kuma monitors.

## Secret Boundary

Never commit real API keys, passwords, VPN credentials, Tailscale auth keys, provider credentials, app databases, or Proxmox private keys. This repo should document what secrets exist and where they belong, but not their values.

Use `notes/media-stack-credentials.md` and relevant `.example` files as pointer documentation.

## Albumary logs

- CT `109` hosts a separate native Grafana/Loki stack at `192.168.1.201`.
- CT `105` forwards the Albumary API and worker journals using Alloy.
- See `notes/albumary-observability-runbook.md` and the Albumary repository's `deploy/observability/README.md`.
