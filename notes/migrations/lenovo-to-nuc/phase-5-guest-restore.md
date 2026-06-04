# Phase 5: Guest Restore

Goal: restore guests onto the NUC in dependency order and verify each one before moving to the next risky dependency.

## Agent Rules

- Ask what the user already restored manually.
- Run read-only checks before restore or config changes.
- Restore from the backup set selected in Phase 2.
- Verify bind mounts and passthrough devices before starting dependent services.
- Do not delete or repurpose CT `103` unless the user explicitly asks.
- If a restored guest gets a different IP than expected, summarize the mismatch before changing docs or service catalog files.

## Pre-Restore Checks

```bash
git status --short
pvesm status
ls -lh /mnt/proxmox-usb-backup/dump
qm list
pct list
cat /etc/pve/storage.cfg
```

## Restore Order

1. CT `102`: AdGuard Home.
2. VM `100`: Home Assistant OS.
3. CT `107`: Tailscale subnet router.
4. CT `104`: active Jellyfin.
5. CT `106`: media stack.
6. CT `105`: Albumary.
7. CT `108`: monitoring.
8. CT `101`: stopped reference container.
9. CT `103`: stale Jellyfin candidate.

This order brings DNS and home automation back early, then remote access, then media dependencies, then observability, then stopped/reference guests.

## Per-Guest Restore Cards

### VM 100: Home Assistant

- Expected URL: `http://192.168.1.187:8123`
- Depends on: Zigbee USB `10c4:ea60` if ZHA is in use.
- Restore check:

```bash
qm config 100
qm status 100
curl -fsS http://192.168.1.187:8123 >/dev/null
```

- Acceptance: Home Assistant UI responds and Zigbee coordinator is visible inside the VM.

### CT 101: Reference Container

- Expected state: stopped unless the user wants it running.
- Expected IP from docs: `192.168.1.50/24`.
- Restore check:

```bash
pct config 101
pct status 101
```

- Acceptance: restored for context or intentionally skipped by user decision.

### CT 102: AdGuard Home

- Expected URL: `http://192.168.1.189`
- Restore check:

```bash
pct config 102
pct status 102
pct exec 102 -- systemctl is-active AdGuardHome
curl -fsS http://192.168.1.189 >/dev/null
```

- Acceptance: AdGuard Home service is active and web UI responds.

### CT 103: Stale Jellyfin Candidate

- Expected state: stopped.
- Do not rely on this container for active Jellyfin service.
- Restore check:

```bash
pct config 103
pct status 103
```

- Acceptance: restored as stopped reference state or intentionally skipped by user decision.

### CT 104: Active Jellyfin

- Expected URL: `http://192.168.1.191:8096`
- Depends on: `/mnt/proxmox-usb-backup/media-stack` mounted as `/media`, Intel iGPU device paths.
- Restore check:

```bash
pct config 104
pct status 104
pct exec 104 -- systemctl is-active jellyfin
pct exec 104 -- test -d /media/library/movies
pct exec 104 -- test -d /media/library/tv
curl -fsS http://192.168.1.191:8096 >/dev/null
```

- Acceptance: Jellyfin is active, UI responds, media folders resolve.

### CT 105: Albumary

- Expected app directory: `/opt/spotify_tracker`.
- Expected SQLite path: `/opt/spotify_tracker/data/spotify_tracker.sqlite`.
- Restore check:

```bash
pct config 105
pct status 105
pct exec 105 -- test -r /opt/spotify_tracker/data/spotify_tracker.sqlite
```

- Acceptance: database exists and app service checks pass according to the current Albumary runbook or service notes.

### CT 106: Media Stack

- Expected URL base: `http://192.168.1.197`
- Depends on: `/data`, `/backups/guest-dumps`, `/backups/media-library-current`, `/dev/net/tun`.
- Restore check:

```bash
pct config 106
pct status 106
pct exec 106 -- test -d /data/library/movies
pct exec 106 -- test -d /data/library/tv
pct exec 106 -- test -d /data/downloads
pct exec 106 -- bash -lc 'cd /opt/media-stack && docker compose ps'
curl -fsS http://192.168.1.197:5055 >/dev/null
curl -fsS http://192.168.1.197:7878 >/dev/null
curl -fsS http://192.168.1.197:8989 >/dev/null
curl -fsS http://192.168.1.197:9696 >/dev/null
curl -fsS http://192.168.1.197:8080 >/dev/null
curl -fsS http://192.168.1.197:8090/health >/dev/null
curl -fsS http://192.168.1.197:6767 >/dev/null
```

- Acceptance: Docker services are running, media paths resolve, and LAN web UIs respond.

### CT 107: Tailscale Subnet Router

- Expected IP: `192.168.1.198`.
- Depends on: `/dev/net/tun`, Tailscale account auth, route approval.
- Restore check:

```bash
pct config 107
pct status 107
pct exec 107 -- tailscale status
pct exec 107 -- sysctl net.ipv4.ip_forward
```

- Acceptance: authenticated in Tailscale, advertises `192.168.1.0/24`, and route is approved in the Tailscale admin console.

### CT 108: Monitoring

- Expected URLs:
  - Grafana: `http://192.168.1.200:3000`
  - Prometheus: `http://192.168.1.200:9090`
  - Uptime Kuma: `http://192.168.1.200:3001`
- Restore check:

```bash
pct config 108
pct status 108
pct exec 108 -- bash -lc 'cd /opt/monitoring && docker compose ps'
curl -fsS http://192.168.1.200:3000/api/health
curl -fsS http://192.168.1.200:9090/-/ready
curl -fsS http://192.168.1.200:3001 >/dev/null
```

- Acceptance: monitoring stack responds and Prometheus targets are healthy.

## Completion Criteria

- Restored guests match the intended scope.
- Each restored service has passed its acceptance check or has a documented exception in the session summary.
- Any IP, mount, device, or service mismatch is summarized before changing canonical docs.
