# Agent Instructions

This repo is the operational memory for a Proxmox home server. Before making changes, read the relevant docs and preserve the no-secrets boundary.

## Start Here

- Read `TODO.md` for the current future-work queue.
- Read `README.md` for repo conventions.
- Read `notes/proxmox-media-inventory.md` for the current Proxmox guests, LAN IPs, and services.
- Read `notes/media-stack-runbook.md` before changing Jellyfin, media services, storage mounts, Docker Compose, VPN routing, or service ports.
- Read `homelab-services.yml` before changing the Home Assistant Homelab dashboard.

## Current Ground Truth

- Proxmox host repo path: `/root/server-admin`
- Home Assistant: VM `100`, LAN `192.168.1.187:8123`
- AdGuard Home: CT `102`, LAN `192.168.1.189`
- Active Jellyfin: CT `104`, LAN `192.168.1.191:8096`
- Stale Jellyfin candidate: CT `103`; do not rely on it unless explicitly asked.
- Media stack: CT `106`, LAN `192.168.1.197`
- Tailscale subnet router: CT `107`, LAN `192.168.1.198`
- Shared media host path: `/srv/media-stack`
- CT `104` media mount: `/media`
- CT `106` media mount: `/data`

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
