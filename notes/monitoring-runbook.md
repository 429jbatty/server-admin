# Monitoring Runbook

This runbook covers the dedicated Grafana-based technical monitoring stack for the Proxmox homelab.

The active host is NUC node `pve-nuc`. From the retired Lenovo workspace, run Proxmox commands through `ssh pve-nuc`.

## Architecture

- CT `108`: `monitoring`, an unprivileged Ubuntu 24.04 LXC on `local-lvm`, LAN `192.168.1.200`.
- Runtime path inside CT `108`: `/opt/monitoring`.
- Repo source path: `monitoring/`.
- Services:
  - Grafana: `http://192.168.1.200:3000`
  - Prometheus: `http://192.168.1.200:9090`
  - Uptime Kuma: `http://192.168.1.200:3001`
  - Proxmox PVE exporter: internal Docker service `pve-exporter:9221`
- Proxmox host exporter:
  - `node_exporter` runs on active NUC node `pve-nuc` at `http://192.168.1.184:9100/metrics`.
  - The existing Home Assistant JSON exporter remains at `http://192.168.1.184:9108/metrics/homelab`.
- Home Assistant exporter:
  - Home Assistant's built-in Prometheus exporter is enabled by the repo-backed package `home-assistant/prometheus_package.yaml`.
  - Prometheus scrapes `http://192.168.1.187:8123/api/prometheus` as job `home-assistant`.
  - The scrape uses a long-lived Home Assistant token stored only in CT `108` at `/opt/monitoring/secrets/home-assistant-prometheus-token`.

Grafana is for technical monitoring, trends, VM/LXC visibility, and alert-oriented views. Home Assistant remains the control dashboard for smart-home devices and high-level service health.

## Paths

Inside CT `108`:

```text
/opt/monitoring/
  docker-compose.yml
  prometheus/prometheus.yml
  grafana/provisioning/
  grafana/dashboards/
  secrets/
```

Secret-bearing files live only inside CT `108`:

```text
/opt/monitoring/secrets/grafana.env
/opt/monitoring/secrets/grafana_admin_password
/opt/monitoring/secrets/pve.yml
/opt/monitoring/secrets/uptime-kuma.env
/opt/monitoring/secrets/home-assistant-prometheus-token
```

The repo tracks only `.example` files for secrets. Do not commit token values or generated passwords.

## Daily Operations

Open Grafana and use the `Homelab / Homelab Overview` dashboard to answer:

- Is the Proxmox host overloaded?
- Is RAM, root disk, or backup HDD usage trending up?
- Are important VMs/LXCs running?
- Are Home Assistant comfort, battery, presence, and chore/status sensors behaving normally?
- Is the metrics pipeline healthy?

Use Uptime Kuma for simple HTTP uptime checks for:

- Home Assistant
- Jellyfin
- AdGuard Home
- Albumary public website
- Grafana
- Prometheus
- Proxmox UI

## Management Commands

```bash
pct exec 108 -- bash -lc 'cd /opt/monitoring && docker compose ps'
pct exec 108 -- bash -lc 'cd /opt/monitoring && docker compose logs --tail=100'
pct exec 108 -- bash -lc 'cd /opt/monitoring && docker compose pull'
pct exec 108 -- bash -lc 'cd /opt/monitoring && docker compose up -d'
```

Check Prometheus configuration:

```bash
pct exec 108 -- bash -lc 'cd /opt/monitoring && docker compose exec -T prometheus promtool check config /etc/prometheus/prometheus.yml'
```

Avoid running `docker compose config` after secret env files exist because Compose expands `env_file` values in its output.

After changing the Home Assistant Prometheus token, restart Prometheus:

```bash
pct exec 108 -- bash -lc 'cd /opt/monitoring && docker compose restart prometheus'
```

Re-run the Uptime Kuma monitor bootstrap:

```bash
pct exec 108 -- bash -lc 'set -a && . /opt/monitoring/secrets/uptime-kuma.env && set +a && /opt/monitoring/venv/bin/python /opt/monitoring/scripts/bootstrap-uptime-kuma.py'
```

## Proxmox API Token

The PVE exporter uses a limited read-only API token:

- User: `prometheus@pve`
- Token: `monitoring`
- Role: `PVEAuditor`
- ACL path: `/`
- Runtime config: `/opt/monitoring/secrets/pve.yml`

If the token must be rotated, recreate the token in Proxmox and replace only the CT-local `token_value` in `/opt/monitoring/secrets/pve.yml`, then restart the exporter:

```bash
pct exec 108 -- bash -lc 'cd /opt/monitoring && docker compose restart pve-exporter prometheus'
```

## Verification

```bash
curl -fsS http://192.168.1.184:9100/metrics >/dev/null
curl -fsS http://192.168.1.200:9090/-/ready
curl -fsS http://192.168.1.200:3000/api/health
curl -fsS http://192.168.1.200:3001
```

The Home Assistant Prometheus endpoint should return `401` without a token and metrics with the CT-local token:

```bash
curl -o /dev/null -sS -w '%{http_code}\n' http://192.168.1.187:8123/api/prometheus
pct exec 108 -- bash -lc 'TOKEN=$(cat /opt/monitoring/secrets/home-assistant-prometheus-token) && curl -fsS -H "Authorization: Bearer ${TOKEN}" http://192.168.1.187:8123/api/prometheus >/dev/null'
```

Prometheus targets should show `prometheus`, `node-exporter`, `pve`, and `home-assistant` as up. Useful PromQL smoke tests:

```text
up
node_load5
node_filesystem_size_bytes{mountpoint="/mnt/proxmox-usb-backup"}
pve_up
pve_guest_info
hass_entity_available
hass_temperature_c
hass_humidity_percent
hass_battery_percent
```

## Expansion Notes

Keep the MVP simple until the basic metrics pipeline is stable. Later additions can include logs, Home Assistant long-term history, custom app exporters, astronomy/satellite dashboards, and richer alert routing. Do not add Loki, Promtail/Alloy, InfluxDB, or Alertmanager unless there is a specific expansion plan.
