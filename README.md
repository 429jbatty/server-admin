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

- Service catalog and dashboard inventory: `homelab-services.yml`
- Proxmox/media inventory and live storage notes: `notes/proxmox-media-inventory.md`
- Operational runbooks: `notes/*-runbook.md`
- Desired non-secret media stack config: `media-stack/`
- Home Assistant dashboard/package sources: `home-assistant/`
- Host and service scripts: `scripts/`
- Systemd unit and timer sources: `systemd/`
- Agent-local workflow notes: `skills/`

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

The dashboard is installed in Home Assistant as a YAML Lovelace dashboard named `Homelab`. Health checks are intentionally lightweight: HTTP reachability for web services and ping reachability for the Tailscale subnet router. Resource metrics come from a LAN-only Proxmox host exporter at `http://192.168.1.184:9108/metrics/homelab`; it publishes CPU, memory, disk, status, uptime, and media-stack Docker container utilization only.

Albumary Cloudflare metrics are fetched by `home-assistant/cloudflare_albumary_metrics.py`, installed in Home Assistant as `/config/scripts/cloudflare_albumary_metrics.py`. The dashboard uses Cloudflare Web Analytics/RUM for `Page views` and `Visitors`, and keeps HTTP Traffic metrics for requests, transfer, status codes, and lightweight reachability context. Store the real values only in Home Assistant `secrets.yaml`:

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
