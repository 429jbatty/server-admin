---
name: homelab-media-stack
description: Operate and troubleshoot this Proxmox homelab media stack with Jellyfin CT 104 and media-services CT 106. Use for safe inspection, LXC or Docker Compose changes, Jellyseerr/Sonarr/Prowlarr request and indexer diagnosis, daily-show season-number mismatches, documentation, and verification without exposing secrets.
---

# Homelab Media Stack

Use this skill for changes to the Proxmox media automation setup in `/root/server-admin`.

## Ground Truth

- Active Jellyfin is CT `104`, Ubuntu 24.04, URL `http://192.168.1.191:8096`.
- CT `103` is a stale Jellyfin candidate. Do not delete, repurpose, or rely on it unless the user explicitly asks.
- Media services live in CT `106`, hostname `media-stack`.
- Shared host path is `/mnt/proxmox-usb-backup/media-stack`.
- CT `104` sees shared media at `/media`.
- CT `106` sees shared media at `/data`.
- qBittorrent has no global download or upload speed limits; CT `106` retains
  its 2-core and 2 GiB RAM resource limits.
- Sonarr manages U.S. `Jeopardy!` (`TVDB 77075`) as a `Daily` series. Its
  TheTVDB metadata uses calendar-year seasons, which do not align with
  Jellyseerr/TMDB broadcast-season requests; manage affected Jeopardy air-date
  ranges directly in Sonarr.
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

When running from the retired Lenovo workspace, quote the complete remote
command so shell operators execute inside CT `106`:

```bash
ssh pve-nuc "pct exec 106 -- bash -lc 'cd /opt/media-stack && docker compose ps'"
```

Do not pass an unquoted semicolon or `&&` through `ssh`; the remote Proxmox
shell can run the remainder on the host instead of in the container.

### Diagnose A TV Request That Finds Nothing

1. Confirm the Jellyseerr request in its logs and read-only SQLite database at
   `/data/config/jellyseerr/db/db.sqlite3`. Inspect only the relevant rows in
   `media`, `media_request`, `season`, and `season_request`; do not print users,
   sessions, settings, or credentials.
2. Confirm the Sonarr series identity, type, season numbers, monitored state,
   and episode air dates through its API. Read the API key at runtime from
   `/data/config/sonarr/config.xml`; never print or persist it.
3. Query Prowlarr directly with `scripts/prowlarr-query.py`. A raw Prowlarr
   match proves indexer availability but not that Sonarr can parse or accept the
   release.
4. Run a Sonarr interactive episode search and inspect Sonarr logs. If Prowlarr
   returns `Show.YYYY.MM.DD` releases while Sonarr reports `daily-style episode
   for non-daily series`, change the Sonarr series type to `Daily`.
5. Compare Jellyseerr/TMDB season numbers with Sonarr/TheTVDB season numbers.
   For year-based metadata, derive the intended episode IDs from an inclusive
   air-date range rather than monitoring both entire calendar years.
6. Check Prowlarr and Sonarr health. An indexer can be enabled and synced but
   excluded from searches after repeated failures.

Use the direct-query helper from this repo by temporarily copying it into CT
`106`:

```bash
ssh pve-nuc pct push 106 /root/server-admin/skills/homelab-media-stack/scripts/prowlarr-query.py /tmp/prowlarr-query.py
ssh pve-nuc "pct exec 106 -- python3 /tmp/prowlarr-query.py --query 'Jeopardy 2018 09 10' --title-contains Jeopardy"
```

### Repair A Daily-Show Date Range

Use `scripts/sonarr-daily-range.py`. It is read-only unless `--apply` or
`--search` is supplied.

1. Run it without mutation flags and require an expected episode count.
2. Review the date boundaries, current series type, monitored counts, and
   out-of-range monitored count.
3. Apply the type and monitoring change. The helper creates an online SQLite
   backup first; use this instead of copying a live WAL-mode database.
4. Verify one boundary date interactively. Require at least one approved result
   before launching the range search.
5. Run `--search` only with explicit user authorization. Sonarr's
   `EpisodeSearch` command automatically grabs accepted releases; it is not a
   read-only search.
6. Monitor `/api/v3/command/<id>`, Sonarr's queue, qBittorrent health, and free
   space. Metadata waits and temporary stalls can clear without intervention.

Jeopardy season 35 example:

```bash
ssh pve-nuc pct push 106 /root/server-admin/skills/homelab-media-stack/scripts/sonarr-daily-range.py /tmp/sonarr-daily-range.py
ssh pve-nuc "pct exec 106 -- python3 /tmp/sonarr-daily-range.py --tvdb-id 77075 --start 2018-09-10 --end 2019-07-26 --expected-count 230"
ssh pve-nuc "pct exec 106 -- python3 /tmp/sonarr-daily-range.py --tvdb-id 77075 --start 2018-09-10 --end 2019-07-26 --expected-count 230 --apply --verify-date 2018-09-10"
ssh pve-nuc "pct exec 106 -- python3 /tmp/sonarr-daily-range.py --tvdb-id 77075 --start 2018-09-10 --end 2019-07-26 --expected-count 230 --verify-date 2018-09-10 --search"
```

Do not treat Jellyseerr's accepted status as proof that Sonarr monitored any
episodes. For U.S. `Jeopardy!`, Jellyseerr season 35 became an accepted request
for nonexistent Sonarr season 35; Sonarr/TheTVDB used 2018 and 2019 instead.

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
- Daily-show repairs have a pre-change Sonarr database backup, exact date/count
  safety checks, and a successful one-episode interactive search before any
  automatic range search.
