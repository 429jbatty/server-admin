# Home server admin workspace

This repo is the operational memory for the Proxmox home server. It keeps the Git-backed source of truth for human notes, AI-agent instructions, service inventory, desired non-secret configuration, runbooks, scripts, systemd units, and Home Assistant dashboard sources.

Do not store secrets here. Use placeholders, `.example` files, and pointer docs for secret-bearing configuration.

## Start Here

- Human overview: `notes/homelab-overview.md`
- Agent instructions: `AGENTS.md`
- Documentation maintenance contract: `notes/documentation-maintenance.md`
- Future-work queue: `TODO.md`
- Proxmox guest and service inventory: `notes/proxmox-media-inventory.md`
- Media stack runbook: `notes/media-stack-runbook.md`
- Backup and restore runbook: `notes/homelab-backup-runbook.md`
- Secret pointer checklist: `notes/media-stack-credentials.md`

## Source Of Truth

- Active Proxmox host: NUC node `pve-nuc` at `192.168.1.184`
- Retired migration source: Lenovo node `proxmox` at `192.168.1.186`
- Service catalog and dashboard inventory: `homelab-services.yml`
- Proxmox/media inventory and live storage notes: `notes/proxmox-media-inventory.md`
- Operational runbooks: `notes/*-runbook.md`
- Desired non-secret media stack config: `media-stack/`
- Home Assistant dashboard/package sources: `home-assistant/`
- Host and service scripts: `scripts/`
- Systemd unit and timer sources: `systemd/`
- Agent-local workflow notes: `skills/`
- Monitoring stack source: `monitoring/`

Keep `homelab-services.yml` as the machine-readable service catalog. Future service additions or LAN IP/port changes should start there, then flow into the Home Assistant package/dashboard files and any affected runbook. Avoid copying the full service table into Markdown unless the duplicate is intentionally maintained.

## Change Workflow

- Run `git status --short` before edits.
- Read the relevant overview, inventory, and runbook before changing infrastructure.
- Compare docs against live read-only checks before changing Proxmox guests, mounts, ports, Docker Compose, VPN routing, backups, or dashboard wiring.
- Keep docs, inventory, scripts, systemd units, and dashboard sources aligned in the same change.
- Run `git diff --check` and review diffs for secrets before committing or pushing.

## Homelab Dashboard

- Service inventory source: `homelab-services.yml`
- Home Assistant package source: `home-assistant/homelab_services_package.yaml`
- Home Assistant Prometheus export source: `home-assistant/prometheus_package.yaml`
- Home Assistant dashboard source: `home-assistant/homelab_dashboard.yaml`
- Proxmox metrics exporter source: `scripts/homelab-metrics-exporter.py`
- Proxmox metrics exporter service: `systemd/homelab-metrics-exporter.service`
- USB backup runbook: `notes/homelab-backup-runbook.md`
- Host backup script source: `scripts/homelab-host-backup.sh`
- Host backup timer source: `systemd/homelab-host-backup.timer`
- File backup script source: `scripts/homelab-file-backup.sh`
- File backup timer source: `systemd/homelab-file-backup.timer`
- Albumary SQLite backup script source: `scripts/albumary-sqlite-backup.sh`
- Albumary SQLite backup timer source: `systemd/albumary-sqlite-backup.timer`
- Local health watchdog script source: `scripts/homelab-health-watchdog.sh`
- Local health watchdog timer source: `systemd/homelab-health-watchdog.timer`

The dashboard is installed in Home Assistant as a YAML Lovelace dashboard named `Homelab`. Health checks are intentionally lightweight: HTTP reachability for web services and ping reachability for the Tailscale subnet router. Resource metrics come from a LAN-only Proxmox host exporter at `http://192.168.1.184:9108/metrics/homelab`; it publishes CPU, memory, disk, status, uptime, and media-stack Docker container utilization only.

Albumary website analytics now live in Grafana. Home Assistant keeps only the simple Albumary public-site reachability sensor. The Cloudflare token and zone ID should be copied from Home Assistant secrets into CT `108` at `/opt/monitoring/secrets/albumary-cloudflare.env`; never store the real values in Git. Home Assistant uses these secret names:

Albumary currently runs in CT `105` from `/opt/spotify_tracker`, with its SQLite database at `/opt/spotify_tracker/data/spotify_tracker.sqlite`. The daily `albumary-sqlite-backup.timer` creates a database-only backup under `/mnt/proxmox-usb-backup/albumary-sqlite/` before the full Proxmox guest backup.

```yaml
cloudflare_api_token: "Bearer ..."
cloudflare_zone_id: "..."
cloudflare_account_id: "..." # optional; discovered from the zone when omitted
cloudflare_albumary_hostname: "app.albumary.net"
```

If using an older Cloudflare global API key instead of an API token, use:

```yaml
cloudflare_api_key: "..."
cloudflare_api_email: "you@example.com"
cloudflare_zone_id: "..."
cloudflare_albumary_hostname: "app.albumary.net"
```

The AdGuard pause button uses the AdGuard Home HTTP API and expects this Home Assistant secret:

```yaml
adguard_auth_header: "Basic BASE64_USERNAME_COLON_PASSWORD"
```

## Technical Monitoring

- Monitoring runbook: `notes/monitoring-runbook.md`
- Monitoring Compose source: `monitoring/docker-compose.yml`
- Prometheus scrape config source: `monitoring/prometheus/prometheus.yml`
- Blackbox exporter config source: `monitoring/prometheus/blackbox.yml`
- Grafana dashboard source: `monitoring/grafana/dashboards/homelab-overview.json`
- Albumary website dashboard source: `monitoring/grafana/dashboards/albumary-website.json`
- Albumary Cloudflare exporter source: `monitoring/scripts/albumary-cloudflare-exporter.py`
- Albumary Cloudflare env example: `monitoring/secrets/albumary-cloudflare.env.example`
- Home Assistant Prometheus token example: `monitoring/secrets/home-assistant-prometheus-token.example`
- Uptime Kuma bootstrap source: `scripts/bootstrap-uptime-kuma.py`

The dedicated monitoring stack runs in CT `108` at `192.168.1.200`. Grafana is the technical monitoring dashboard for server health, trends, storage, VM/LXC visibility, and alert-oriented views. Home Assistant remains the control dashboard for smart-home devices.

Runtime services are LAN-only:

- Grafana: `http://192.168.1.200:3000`
- Prometheus: `http://192.168.1.200:9090`
- Uptime Kuma: `http://192.168.1.200:3001`
- Host node_exporter: `http://192.168.1.184:9100/metrics`
- Home Assistant Prometheus export: `http://192.168.1.187:8123/api/prometheus`
- Albumary Cloudflare exporter: internal Docker service `albumary-cloudflare-exporter:9210`
- Blackbox exporter: internal Docker service `blackbox-exporter:9115`

Secret-bearing monitoring files live only inside CT `108` under `/opt/monitoring/secrets/`. The repo tracks only `.example` templates.
The Home Assistant scrape token belongs at `/opt/monitoring/secrets/home-assistant-prometheus-token` and must be a long-lived Home Assistant access token without any `Bearer ` prefix.
The Albumary Cloudflare env file belongs at `/opt/monitoring/secrets/albumary-cloudflare.env` and may reuse the existing Home Assistant Cloudflare token and zone ID.

## Resilience And Auto-Recovery

The active single-node recovery model is layered:

- Proxmox starts VM `100` and CTs `102`, `104`, `105`, `106`, `107`, and `108`
  automatically after host boot.
- Startup ordering is explicit: AdGuard first, Home Assistant/Jellyfin/Albumary
  and remote access next, media stack after those, and monitoring last.
- Docker Compose services in CT `106` and CT `108` use `restart:
  unless-stopped` for app-level process recovery.
- Proxmox `watchdog-mux` is configured in `/etc/default/pve-ha-manager` to load
  the ACPI hardware watchdog module `wdat_wdt` on startup. Do not install
  or enable a separate watchdog daemon without a new plan; `watchdog-mux` should
  own `/dev/watchdog`.
- `homelab-health-watchdog.timer` is a separate local health-check timer, not a
  Linux watchdog daemon. It runs `/usr/local/sbin/homelab-health-watchdog` every
  5 minutes after boot, checks critical local Proxmox services and commands,
  tracks consecutive failures in `/var/lib/homelab-health-watchdog/`, saves
  diagnostic bundles under `/var/log/homelab-health-watchdog/`, and reboots only
  after 3 consecutive failed runs.

Install or update the local health watchdog on `pve-nuc` from this repo with:

```bash
install -m 0755 scripts/homelab-health-watchdog.sh /usr/local/sbin/homelab-health-watchdog
install -m 0644 systemd/homelab-health-watchdog.service /etc/systemd/system/homelab-health-watchdog.service
install -m 0644 systemd/homelab-health-watchdog.timer /etc/systemd/system/homelab-health-watchdog.timer
systemctl daemon-reload
systemctl enable --now homelab-health-watchdog.timer
```

Optional non-secret runtime overrides belong in
`/etc/default/homelab-health-watchdog`; use
`systemd/homelab-health-watchdog.default.example` as the template. To verify
without risking a reboot, run:

```bash
DRY_RUN=1 /usr/local/sbin/homelab-health-watchdog
systemctl list-timers homelab-health-watchdog.timer
```

This is not multi-node HA. A watchdog-triggered reboot can recover from host
hangs, but disk failure, broken guest config, corrupt data, or dead hardware
still requires the backup and restore process in `notes/homelab-backup-runbook.md`.
