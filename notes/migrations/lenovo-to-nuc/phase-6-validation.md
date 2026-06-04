# Phase 6: Validation

Goal: confirm the NUC migration is functionally complete and identify any docs that must be updated because ground truth changed.

## Agent Rules

- Use live checks, not memory.
- Use `../../../homelab-services.yml` as the service catalog for dashboard-visible services.
- If a service fails, distinguish between "not restored yet", "restored but unhealthy", and "intentionally changed".
- Do not update canonical docs until the live state is verified.

## Host Checks

```bash
hostnamectl
pveversion -v
cat /etc/network/interfaces
pvesm status
findmnt /mnt/proxmox-usb-backup
qm list
pct list
systemctl list-timers homelab-host-backup.timer
systemctl list-timers homelab-file-backup.timer
systemctl list-timers albumary-sqlite-backup.timer
systemctl status homelab-metrics-exporter.service --no-pager
curl -fsS http://192.168.1.184:9108/metrics/homelab >/dev/null
curl -fsS http://192.168.1.184:9100/metrics >/dev/null
```

## Service Checks

Core:

```bash
curl -fsS http://192.168.1.187:8123 >/dev/null
curl -fsS http://192.168.1.189 >/dev/null
```

Media:

```bash
curl -fsS http://192.168.1.191:8096 >/dev/null
curl -fsS http://192.168.1.197:5055 >/dev/null
curl -fsS http://192.168.1.197:7878 >/dev/null
curl -fsS http://192.168.1.197:8989 >/dev/null
curl -fsS http://192.168.1.197:9696 >/dev/null
curl -fsS http://192.168.1.197:8080 >/dev/null
curl -fsS http://192.168.1.197:8090/health >/dev/null
curl -fsS http://192.168.1.197:6767 >/dev/null
```

Remote access:

```bash
pct exec 107 -- tailscale status
pct exec 107 -- tailscale ip -4
```

Monitoring:

```bash
curl -fsS http://192.168.1.200:3000/api/health
curl -fsS http://192.168.1.200:9090/-/ready
curl -fsS http://192.168.1.200:3001 >/dev/null
pct exec 108 -- bash -lc 'cd /opt/monitoring && docker compose ps'
```

Backups:

```bash
findmnt /mnt/proxmox-usb-backup
pvesm status
ls -lh /mnt/proxmox-usb-backup/dump
ls -lh /mnt/proxmox-usb-backup/host-config
ls -lh /mnt/proxmox-usb-backup/file-backups/srv-media-stack
ls -lh /mnt/proxmox-usb-backup/albumary-sqlite
```

## Application-Level Checks

- Home Assistant: dashboard loads, critical integrations are present, Zigbee coordinator is online.
- AdGuard Home: DNS clients are using the restored service as expected.
- Jellyfin: libraries are visible and playback starts.
- Radarr/Sonarr: root folders resolve to `/data/library/...`.
- qBittorrent: categories exist for `radarr` and `sonarr`; no router port forward is created.
- Prowlarr: applications sync to Radarr and Sonarr.
- FileBrowser Quantum: media library source works and backup sources are read-only.
- Tailscale: remote client can reach LAN services through CT `107`.
- Grafana/Prometheus/Uptime Kuma: core targets are up.

## Docs To Reconcile After Verified Changes

Update only if live ground truth changed:

- `../../homelab-overview.md`
- `../../proxmox-media-inventory.md`
- `../../homelab-backup-runbook.md`
- `../../media-stack-runbook.md`
- `../../monitoring-runbook.md`
- `../../../homelab-services.yml`
- Home Assistant dashboard/package files under `../../../home-assistant/`

## Completion Criteria

- NUC is the active Proxmox host.
- Required guests are restored and validated.
- USB HDD, media paths, backups, and device passthrough are working.
- Dashboard-visible services match `homelab-services.yml` or documented intentional changes.
- Any canonical docs affected by real changes are updated in the same final migration change.
