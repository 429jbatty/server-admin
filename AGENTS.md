# Agent Instructions

This repo is the operational memory for a Proxmox home server. Before making changes, read the relevant docs and preserve the no-secrets boundary.

## Start Here

- Read `TODO.md` for the current future-work queue.
- Read `README.md` for repo conventions.
- Read `notes/homelab-overview.md` for the high-level architecture map.
- Read `notes/documentation-maintenance.md` before changing docs, service inventory, dashboard sources, scripts, or systemd units.
- Read `notes/proxmox-media-inventory.md` for the current Proxmox guests, LAN IPs, and services.
- Read `notes/media-stack-runbook.md` before changing Jellyfin, media services, storage mounts, Docker Compose, VPN routing, or service ports.
- Read `notes/homelab-backup-runbook.md` before changing backups, restore flows, backup storage, or backup timers.
- Read `homelab-services.yml` before changing the Home Assistant Homelab dashboard.

## Current Ground Truth

- Proxmox host repo path: `/root/server-admin`
- Home Assistant: VM `100`, LAN `192.168.1.187:8123`
- AdGuard Home: CT `102`, LAN `192.168.1.189`
- Active Jellyfin: CT `104`, LAN `192.168.1.191:8096`
- Stale Jellyfin candidate: CT `103`; do not rely on it unless explicitly asked.
- Media stack: CT `106`, LAN `192.168.1.197`
- Tailscale subnet router: CT `107`, LAN `192.168.1.198`
- Shared media host path: `/mnt/proxmox-usb-backup/media-stack`
- CT `104` media mount: `/media`
- CT `106` media mount: `/data`

## Freshness Rules

- Treat this repo as the canonical source of truth for docs, desired configuration, service inventory, scripts, and non-secret templates.
- Before infrastructure changes, compare the relevant docs with live read-only checks. At minimum, check `git status --short` and inspect the affected inventory, runbook, service catalog, script, or unit files.
- If live state and docs disagree, do not silently pick one. Verify the live state with read-only commands, then update the docs in the same change as the infrastructure work.
- Keep `homelab-services.yml` as the machine-readable service catalog for dashboard-visible services. Do not duplicate its full service table into Markdown unless there is a specific reason.
- When adding or changing a service, update the service catalog first, then update mirrored Home Assistant dashboard/package files if needed.

## Documentation Update Checklist

- Service, LAN IP, port, URL, owner VMID/CTID, health check, or dashboard visibility changed: update `homelab-services.yml`, `README.md` if the doc map changes, `notes/proxmox-media-inventory.md`, and any relevant runbook.
- Proxmox guest, mount point, passthrough device, storage path, or resource allocation changed: update `notes/proxmox-media-inventory.md` and the affected runbook; back up guest configs before mount, device, or resource changes.
- Jellyfin, media services, Docker Compose, VPN routing, FileBrowser, or media storage changed: update `notes/media-stack-runbook.md`, `media-stack/` templates, and `skills/homelab-media-stack/SKILL.md` when its ground truth changes.
- Backup job, restore process, backup target, script, or timer changed: update `notes/homelab-backup-runbook.md`, `TODO.md` if future work changes, and the matching files under `scripts/` or `systemd/`.
- Home Assistant dashboard behavior changed: update `homelab-services.yml`, `home-assistant/homelab_services_package.yaml`, and `home-assistant/homelab_dashboard.yaml` together.
- New operational script or systemd unit added: document its purpose, install location, verification command, and secret boundary in `README.md` or the relevant runbook.
- Secret-bearing setup changed: update pointer/checklist docs only. Never store real secret values in Git.

## Safety Rules

- Never commit secrets.
- Never commit API keys, passwords, VPN credentials, Tailscale auth keys, provider credentials, app databases, or Proxmox private keys.
- Never commit `/etc/pve/priv/*`.
- Use placeholders and `.example` files for secret-bearing config.
- Back up Proxmox guest configs before changing LXC mount points, device passthrough, or resources.
- Keep CT `104` focused on Jellyfin.
- Put media automation services in CT `106`.
- Keep services LAN-only unless the user asks for a specific exposure plan.

## Git Expectations

- Check `git status --short` before edits.
- Do not revert user changes unless explicitly asked.
- Keep docs, inventory, and runbooks aligned with any infrastructure change.
- Run `git diff --check` before committing.
- Review diffs for secrets before committing or pushing.

## Useful Read-Only Checks

- `pct list`
- `qm list`
- `pct config 104`
- `pct config 106`
- `pct config 107`
- `pct exec 104 -- systemctl is-active jellyfin`
- `pct exec 106 -- bash -lc 'cd /opt/media-stack && docker compose ps'`
- `qm guest exec 100 -- ha core check`
