# Media Stack Runbook

This runbook covers the local lightweight media automation stack for Jellyfin.

## Architecture

- CT `104`: active Jellyfin server at `http://192.168.1.191:8096`
- CT `106`: Docker Compose media-services host at `192.168.1.197`
- Shared host storage: `/srv/media-stack`
- CT `104` media path: `/media`
- CT `106` media path: `/data`

The shared storage is intentionally lightweight. It is fine for setup, testing, and a small library, but a dedicated disk or NAS should replace it before building a large media collection.

## Paths

Host:

```text
/srv/media-stack/
  config/
  downloads/
    complete/
      radarr/
      sonarr/
    incomplete/
  library/
    movies/
    tv/
```

Inside CT `104`:

```text
/media/library/movies
/media/library/tv
```

Inside CT `106`:

```text
/data/library/movies
/data/library/tv
/data/downloads
/opt/media-stack/docker-compose.yml
```

## Daily Operations

- Jellyfin: `http://192.168.1.191:8096`
- Jellyseerr: `http://192.168.1.197:5055`
- Radarr: `http://192.168.1.197:7878`
- Sonarr: `http://192.168.1.197:8989`
- Prowlarr: `http://192.168.1.197:9696`
- qBittorrent: `http://192.168.1.197:8080`
- Bazarr: `http://192.168.1.197:6767`

Use Jellyseerr as the main request/search UI. Radarr and Sonarr manage movies and TV. Prowlarr manages lawful/public-domain/owned-media sources and syncs them to Radarr/Sonarr. qBittorrent is the download client.

## Current Integrations

- Radarr root folder: `/data/library/movies`
- Sonarr root folder: `/data/library/tv`
- Radarr and Sonarr both have qBittorrent configured as a download client.
- Prowlarr is connected to Radarr and Sonarr for application sync.
- Internet Archive is configured in Prowlarr and synced to Radarr/Sonarr.
- Internet Archive settings:
  - Base URL: `https://archive.org/`
  - App profile: `Standard`
  - Minimum seeders: `1`
  - Search only in title: enabled
  - Magnet links allowed; `.torrent` downloads allowed
  - Sort: created, descending

Use Internet Archive for public-domain and freely licensed items. Search results can be uneven because archive metadata is less structured than commercial media indexers.

The source Compose file is tracked at `media-stack/docker-compose.yml` and copied into CT `106` at `/opt/media-stack/docker-compose.yml`.
The helper `scripts/configure-media-stack.py` was used to set root folders, qBittorrent, and Prowlarr app sync without writing API keys to the repo.

## Backups

Before major changes:

```bash
mkdir -p /root/server-admin/backups
cp /etc/pve/nodes/proxmox/lxc/104.conf /root/server-admin/backups/104.conf.$(date +%Y%m%d-%H%M%S)
pct exec 104 -- tar -czf /tmp/jellyfin-config-backup.tgz /etc/jellyfin /var/lib/jellyfin
pct pull 104 /tmp/jellyfin-config-backup.tgz /root/server-admin/backups/jellyfin-104-config.$(date +%Y%m%d-%H%M%S).tgz
```

For full LXC backups, prefer Proxmox `vzdump` when there is enough free space:

```bash
vzdump 104 --mode snapshot --storage local --compress zstd
vzdump 106 --mode snapshot --storage local --compress zstd
```

## Updates

Inside CT `106`:

```bash
cd /opt/media-stack
docker compose pull
docker compose up -d
docker image prune -f
```

Check health:

```bash
docker compose ps
docker compose logs --tail=100
```

## Restore Notes

- Restore Jellyfin metadata from the latest `jellyfin-104-config.*.tgz` backup only onto CT `104`.
- Restore `/opt/media-stack/docker-compose.yml` and `/srv/media-stack/config` for CT `106` services.
- Recreate bind mounts before restarting Jellyfin or Docker Compose.

## Future Storage Migration

When a larger disk or NAS exists:

1. Stop CT `106` Docker services.
2. Stop Jellyfin in CT `104`.
3. Copy `/srv/media-stack` to the new storage location with ownership and permissions preserved.
4. Update CT `104` and CT `106` mount points to the new host path.
5. Start Jellyfin and Docker services.
6. Verify Radarr/Sonarr root folders and Jellyfin libraries still resolve.

## Troubleshooting

- If Jellyfin cannot see media, verify CT `104` has `/media/library/movies` and `/media/library/tv`.
- If Radarr/Sonarr cannot import downloads, verify CT `106` has `/data/downloads` and `/data/library`.
- If qBittorrent login fails, check its container logs for the temporary password, then set a permanent password in the UI.
- If Docker services restart repeatedly, run `docker compose logs --tail=200 <service>`.
- If CT `106` has no IP, check Proxmox DHCP, bridge `vmbr0`, and `pct config 106`.

## Security Notes

- LAN-only by default.
- Do not expose these services publicly without a separate reverse-proxy/auth/VPN plan.
- Do not commit API keys, passwords, provider credentials, or indexer credentials.
