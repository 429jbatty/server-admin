---
name: homelab-media-stack
description: Use when working on this Proxmox homelab media stack with Jellyfin CT 104 and media-services CT 106. Covers safe inspection, LXC changes, Docker Compose updates, documentation, and verification without storing secrets.
---

# Homelab Media Stack

Use this skill for changes to the Proxmox media automation setup in `/root/server-admin`.

## Ground Truth

- Active Jellyfin is CT `104`, Ubuntu 24.04, URL `http://192.168.1.191:8096`.
- CT `103` is a stale Jellyfin candidate. Do not delete, repurpose, or rely on it unless the user explicitly asks.
- Media services live in CT `106`, hostname `media-stack`.
- Shared host path is `/srv/media-stack`.
- CT `104` sees shared media at `/media`.
- CT `106` sees shared media at `/data`.
- Repo docs live under `notes/`.

## Safety Rules

- Never commit secrets. Use placeholders for API keys, passwords, VPN credentials, provider credentials, and indexer credentials.
- Back up CT configs before changing Proxmox mount points or resources.
- Prefer read-only inspection first:
  - `pct list`
  - `pct config 104`
  - `pct config 106`
  - `pct exec 104 -- systemctl status jellyfin --no-pager`
  - `pct exec 106 -- docker compose -f /opt/media-stack/docker-compose.yml ps`
- Keep CT `104` focused on Jellyfin. Put automation services in CT `106`.
- Keep services LAN-only unless the user asks for a separate remote-access plan.

## Common Tasks

### Inspect

1. Check `notes/proxmox-media-inventory.md` and `notes/media-stack-runbook.md`.
2. Confirm current Proxmox state with `pct list`, `pct config 104`, and `pct config 106`.
3. Confirm Jellyfin with `pct exec 104 -- systemctl is-active jellyfin`.
4. Confirm Compose services with `pct exec 106 -- bash -lc 'cd /opt/media-stack && docker compose ps'`.

### Update Compose

1. Edit `/opt/media-stack/docker-compose.yml` inside CT `106` or update the documented source if one is added to the repo.
2. Run `docker compose config` before applying.
3. Apply with `docker compose up -d`.
4. Verify service ports and logs.
5. Update the runbook when ports, paths, or service behavior changes.

### Add Storage

1. Create or identify the host path.
2. Stop affected services.
3. Add Proxmox `mp` bind mounts to CT `104` and CT `106`.
4. Verify paths inside both containers.
5. Update inventory and runbook.

## Verification Checklist

- CT `104` Jellyfin active.
- CT `104` can list `/media/library/movies` and `/media/library/tv`.
- CT `106` Docker active.
- CT `106` can list `/data/library/movies`, `/data/library/tv`, and `/data/downloads`.
- Jellyseerr, Radarr, Sonarr, Prowlarr, qBittorrent, and Bazarr ports respond on the CT `106` IP.
- Docs contain no real secrets.
