# Documentation Maintenance

This repo is the source of truth for non-secret operational memory. Future agents should be able to understand and safely update the home server without rediscovering the system from scratch.

## Documentation Contract

- Keep `/root/server-admin` as the canonical documentation home.
- Keep Markdown for human and agent context, YAML for machine-readable service inventory, and `.example` files for secret-bearing templates.
- Keep `homelab-services.yml` as the source of truth for dashboard-visible services and health checks.
- Link to canonical files instead of copying long tables into multiple notes.
- Update docs in the same change as infrastructure changes.
- Do not commit real secrets, app databases, private keys, provider credentials, Tailscale auth keys, or `/etc/pve/priv/*`.

## Before Changes

- Run `git status --short`.
- Read `README.md`, `AGENTS.md`, `notes/homelab-overview.md`, and the affected runbook.
- Check `TODO.md` for related future work.
- Use read-only live checks to confirm current state before touching infrastructure:
  - `pct list`
  - `qm list`
  - `pct config <vmid-or-ctid>`
  - service-specific health checks from the relevant runbook
- If docs and live state disagree, verify live state first and update the stale documentation as part of the same change.

## What To Update Together

- Service added, removed, renamed, moved, exposed, or hidden from the dashboard: update `homelab-services.yml`, Home Assistant dashboard/package sources under `home-assistant/`, `notes/proxmox-media-inventory.md`, and affected runbooks.
- LAN IP, port, URL, service owner, category, description, or health check changed: update `homelab-services.yml` first, then all docs or dashboard files that mention the changed field.
- Proxmox VM/LXC state, storage, mount point, passthrough device, resource allocation, or host path changed: update `notes/proxmox-media-inventory.md` and the affected runbook. Back up guest configs before changing mount points, passthrough devices, or resources.
- Jellyfin, media stack, Docker Compose, qBittorrent, Prowlarr, Radarr, Sonarr, Jellyseerr, Bazarr, FileBrowser, Gluetun, VPN routing, or media paths changed: update `notes/media-stack-runbook.md`, `media-stack/` templates, and `skills/homelab-media-stack/SKILL.md` if its ground truth changes.
- Backup target, schedule, retention, restore process, backup script, or systemd timer changed: update `notes/homelab-backup-runbook.md`, `TODO.md` if future work changed, and the matching files under `scripts/` or `systemd/`.
- New script or systemd unit added: document the source file, installed location, purpose, verification command, and secret boundary in `README.md` or the relevant runbook.
- Credential or secret handling changed: update pointer docs and `.example` files only. Store real values outside Git.

## Before Commit Or Push

- Run `git diff --check`.
- Review the diff for secrets and accidental generated noise.
- Confirm docs agree on core ground truth:
  - Active Jellyfin: CT `104`, `192.168.1.191:8096`.
  - Media stack: CT `106`, `192.168.1.197`.
  - Tailscale subnet router: CT `107`, `192.168.1.198`.
  - Shared media host path: `/mnt/proxmox-usb-backup/media-stack`.
  - Dashboard/service catalog source: `homelab-services.yml`.
- Commit after meaningful infrastructure or documentation changes, then push to the private remote after reviewing for secrets.

## Secret Pointers

The repo may document that a secret exists, the runtime path where it belongs, and the placeholder key name. It must not store real values.

Use this pattern:

```yaml
example_key: "replace-me"
```

Avoid this pattern:

```yaml
example_key: "real-token-or-password"
```
