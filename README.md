# Home server admin workspace

This repo is for Codex-assisted server setup and documentation.
Do not store secrets here.

## Homelab Dashboard

- Service inventory source: `homelab-services.yml`
- Home Assistant package source: `home-assistant/homelab_services_package.yaml`
- Home Assistant dashboard source: `home-assistant/homelab_dashboard.yaml`

The dashboard is installed in Home Assistant as a YAML Lovelace dashboard named `Homelab`. Health checks are intentionally lightweight: HTTP reachability for web services and ping reachability for the Tailscale subnet router.
