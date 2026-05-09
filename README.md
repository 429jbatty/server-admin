# Home server admin workspace

This repo is for Codex-assisted server setup and documentation.
Do not store secrets here.

## Homelab Dashboard

- Service inventory source: `homelab-services.yml`
- Home Assistant package source: `home-assistant/homelab_services_package.yaml`
- Home Assistant dashboard source: `home-assistant/homelab_dashboard.yaml`
- Proxmox metrics exporter source: `scripts/homelab-metrics-exporter.py`
- Proxmox metrics exporter service: `systemd/homelab-metrics-exporter.service`

The dashboard is installed in Home Assistant as a YAML Lovelace dashboard named `Homelab`. Health checks are intentionally lightweight: HTTP reachability for web services and ping reachability for the Tailscale subnet router. Resource metrics come from a LAN-only Proxmox host exporter at `http://192.168.1.184:9108/metrics/homelab`; it publishes CPU, memory, disk, status, uptime, and media-stack Docker container utilization only.

Albumary Cloudflare metrics are fetched by `home-assistant/cloudflare_albumary_metrics.py`, installed in Home Assistant as `/config/scripts/cloudflare_albumary_metrics.py`. Store the real values only in Home Assistant `secrets.yaml`:

```yaml
cloudflare_api_token: "Bearer ..."
cloudflare_zone_id: "..."
cloudflare_albumary_hostname: "app.albumary.net"
```

If using an older Cloudflare global API key instead of an API token, use:

```yaml
cloudflare_api_key: "..."
cloudflare_api_email: "you@example.com"
cloudflare_zone_id: "..."
cloudflare_albumary_hostname: "app.albumary.net"
```
