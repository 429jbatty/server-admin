# Media Stack Runbook

This runbook covers the local lightweight media automation stack for Jellyfin.

## Architecture

- CT `104`: active Jellyfin server at `http://192.168.1.191:8096`
- CT `106`: Docker Compose media-services and FileBrowser Quantum host at `192.168.1.197`
- CT `107`: Tailscale subnet router for remote access to `192.168.1.0/24`
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
/backups/guest-dumps
/backups/media-library-current
/opt/media-stack/docker-compose.yml
/opt/media-stack/filebrowser.env
/opt/media-stack/vpn.env
```

## Daily Operations

- Jellyfin: `http://192.168.1.191:8096`
- Jellyseerr: `http://192.168.1.197:5055`
- Radarr: `http://192.168.1.197:7878`
- Sonarr: `http://192.168.1.197:8989`
- Prowlarr: `http://192.168.1.197:9696`
- qBittorrent: `http://192.168.1.197:8080`
- FileBrowser Quantum: `http://192.168.1.197:8090`
- Bazarr: `http://192.168.1.197:6767`

Use Jellyseerr as the main request/search UI. Radarr and Sonarr manage movies and TV. Prowlarr manages lawful/public-domain/owned-media sources and syncs them to Radarr/Sonarr. qBittorrent is the download client.

Use FileBrowser Quantum for LAN-only file browsing. The admin account can manage users and write to the media library because `/data/library` is mounted read-write. The viewer account is non-admin and defaults to media-library read/download access only. Backup sources are mounted read-only into CT `106` and are not default-enabled for standard users:

- `/backups/guest-dumps`: Proxmox guest backup archives from `/mnt/proxmox-usb-backup/dump`
- `/backups/media-library-current`: latest media-library file-backup snapshot, currently mounted from `/mnt/proxmox-usb-backup/file-backups/srv-media-stack/snapshots/20260512-015501/library`

Proxmox rejects bind mounts through the `current` symlink, so the media-library backup browse mount uses the resolved snapshot directory. To browse a newer snapshot, update CT `106` `mp2` to the new resolved `current/library` target and restart CT `106`.

Do not expose FileBrowser Quantum through router port forwards. Use Tailscale for remote private access.

When away from home, connect the client device to Tailscale and use the same LAN URLs above. The subnet router is CT `107` and advertises `192.168.1.0/24`; do not expose these service ports through the home router.

## Current Integrations

- Radarr root folder: `/data/library/movies`
- Sonarr root folder: `/data/library/tv`
- Radarr and Sonarr both have qBittorrent configured as a download client.
- Prowlarr is connected to Radarr and Sonarr for application sync.
- FileBrowser Quantum is configured from `/data/config/filebrowser/config.yaml`, with secrets in `/opt/media-stack/filebrowser.env`.
- Internet Archive is configured in Prowlarr and synced to Radarr/Sonarr.
- Internet Archive settings:
  - Base URL: `https://archive.org/`
  - App profile: `Standard`
  - Minimum seeders: `1`
  - Search only in title: enabled
  - Magnet links allowed; `.torrent` downloads allowed
  - Sort: created, descending

If Prowlarr times out against Archive.org, use HTTP/1.1 only by setting `DOTNET_SYSTEM_NET_HTTP_SOCKETSHTTPHANDLER_HTTP2SUPPORT=false` for the Prowlarr container.

Use Internet Archive for public-domain and freely licensed items. Search results can be uneven because archive metadata is less structured than commercial media indexers.

The source Compose file is tracked at `media-stack/docker-compose.yml` and copied into CT `106` at `/opt/media-stack/docker-compose.yml`.
The helper `scripts/configure-media-stack.py` was used to set root folders, qBittorrent, and Prowlarr app sync without writing API keys to the repo.

## VPN Layout

- Remote access uses Tailscale in CT `107`; it is separate from the outbound commercial VPN.
- Outbound VPN privacy uses Gluetun in CT `106`.
- qBittorrent and Prowlarr share Gluetun's network namespace, so their Web UIs are published by Gluetun.
- Jellyfin, Jellyseerr, Radarr, Sonarr, and Bazarr stay on normal LAN/Docker networking.
- Store Proton WireGuard settings in `/opt/media-stack/vpn.env` inside CT `106`; use `media-stack/vpn.env.example` as the non-secret template.

To activate Tailscale after installation or re-authentication:

```bash
pct exec 107 -- tailscale up --advertise-routes=192.168.1.0/24 --accept-dns=false --hostname=remote-access
```

Then approve the advertised route in the Tailscale admin console and disable key expiry for CT `107`.

The candidate VPN Compose file is also staged in CT `106` at `/opt/media-stack/docker-compose.vpn-staged.yml`. To activate the outbound VPN after `/opt/media-stack/vpn.env` contains real provider values:

```bash
cp /root/server-admin/media-stack/docker-compose.yml /tmp/docker-compose.yml
pct push 106 /tmp/docker-compose.yml /opt/media-stack/docker-compose.yml
pct exec 106 -- bash -lc 'cd /opt/media-stack && docker compose config'
pct exec 106 -- bash -lc 'cd /opt/media-stack && docker compose up -d'
```

After activation, Radarr and Sonarr should use `gluetun` port `8080` as the qBittorrent download-client host. Prowlarr application URLs for Radarr/Sonarr should keep pointing to the normal Radarr/Sonarr service addresses. Gluetun's `VPN_PORT_FORWARDING_UP_COMMAND` automatically sets qBittorrent's listening port to the Proton forwarded port shown in `/data/config/gluetun/forwarded_port`, and `VPN_PORT_FORWARDING_DOWN_COMMAND` parks qBittorrent on loopback when forwarding drops. qBittorrent must keep localhost Web UI auth bypass enabled so Gluetun can call its API from the shared network namespace. Do not create a router port forward for qBittorrent.

Verification:

```bash
pct exec 106 -- bash -lc 'cd /opt/media-stack && docker compose ps'
pct exec 106 -- bash -lc 'curl -fsS http://127.0.0.1:8090/health'
pct exec 106 -- bash -lc 'docker inspect --format "{{.Name}} {{.HostConfig.NetworkMode}} {{json .HostConfig.PortBindings}}" qbittorrent gluetun prowlarr'
pct exec 106 -- bash -lc 'docker exec gluetun wget -qO- https://ifconfig.me || true'
pct exec 106 -- bash -lc 'docker exec prowlarr curl -fsS https://ifconfig.me || true'
pct exec 106 -- bash -lc 'cat /data/config/gluetun/forwarded_port'
pct exec 106 -- bash -lc 'docker exec gluetun wget -qO- http://127.0.0.1:8080/api/v2/app/preferences | python3 -c "import json,sys; d=json.load(sys.stdin); print({k:d.get(k) for k in (\"listen_port\",\"current_network_interface\",\"random_port\",\"upnp\")})"'
pct exec 106 -- bash -lc 'grep -E "^(Session\\\\Port|Connection\\\\PortRangeMin|Connection\\\\Interface)=" /data/config/qbittorrent/qBittorrent/qBittorrent.conf'
```

qBittorrent and Prowlarr should report `NetworkMode=container:<gluetun-id>` or equivalent and have no direct port bindings of their own. Gluetun should publish `8080` and `9696`. Radarr, Sonarr, Jellyseerr, Bazarr, and CT `104` Jellyfin should remain on normal networking and show the normal WAN IP, not the VPN exit IP.

## Backups

Before major changes:

```bash
mkdir -p /root/server-admin/backups
cp /etc/pve/nodes/proxmox/lxc/104.conf /root/server-admin/backups/104.conf.$(date +%Y%m%d-%H%M%S)
cp /etc/pve/nodes/proxmox/lxc/106.conf /root/server-admin/backups/106.conf.$(date +%Y%m%d-%H%M%S)
cp /etc/pve/nodes/proxmox/lxc/107.conf /root/server-admin/backups/107.conf.$(date +%Y%m%d-%H%M%S)
pct exec 104 -- tar -czf /tmp/jellyfin-config-backup.tgz /etc/jellyfin /var/lib/jellyfin
pct pull 104 /tmp/jellyfin-config-backup.tgz /root/server-admin/backups/jellyfin-104-config.$(date +%Y%m%d-%H%M%S).tgz
```

For full LXC backups, prefer Proxmox `vzdump` when there is enough free space:

```bash
vzdump 104 --mode snapshot --storage local --compress zstd
vzdump 106 --mode snapshot --storage local --compress zstd
vzdump 107 --mode snapshot --storage local --compress zstd
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
- Restore FileBrowser Quantum from `/srv/media-stack/config/filebrowser` and recreate `/opt/media-stack/filebrowser.env` with fresh secrets if it is missing.
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
- If FileBrowser cannot see backups, verify CT `106` has `/backups/guest-dumps` and `/backups/media-library-current`; both should be read-only.
- If qBittorrent login fails, check its container logs for the temporary password, then set a permanent password in the UI.
- If qBittorrent has no internet after VPN activation, check Gluetun first: `pct exec 106 -- bash -lc 'cd /opt/media-stack && docker compose logs --tail=200 gluetun'`.
- If qBittorrent can download but has poor peer connectivity, verify the VPN provider has a forwarded port and that qBittorrent is listening on that same port. Check Gluetun's port-forwarding logs and compare `/data/config/gluetun/forwarded_port` with qBittorrent's `Session\Port`.
- If remote access fails, confirm CT `107` is running, `tailscale status` is authenticated, and the `192.168.1.0/24` route is approved in Tailscale.
- If Docker services restart repeatedly, run `docker compose logs --tail=200 <service>`.
- If CT `106` has no IP, check Proxmox DHCP, bridge `vmbr0`, and `pct config 106`.

## Security Notes

- LAN-only by default.
- Use Tailscale for private remote access instead of public router port forwards.
- Route only qBittorrent and Prowlarr through the commercial VPN unless there is a specific reason to expand scope.
- Do not expose Jellyfin, qBittorrent, Radarr, Sonarr, Prowlarr, Jellyseerr, FileBrowser Quantum, or Bazarr publicly without a separate reverse-proxy/auth plan.
- Do not commit API keys, passwords, provider credentials, VPN keys, forwarded ports, or indexer credentials.
