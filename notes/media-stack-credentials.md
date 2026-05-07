# Media Stack Credentials Checklist

Do not store real secrets in this repository.

## Jellyfin

- URL: `http://192.168.1.191:8096`
- Admin user: document outside this repo
- API key: document outside this repo

## Jellyseerr

- Initial admin account: create in the web UI
- Jellyfin connection:
  - Server URL: `http://192.168.1.191:8096`
  - API key: store outside this repo
- Radarr API key: store outside this repo
- Sonarr API key: store outside this repo

## Radarr

- URL: `http://192.168.1.197:7878`
- API key: store outside this repo
- Root folder: `/data/library/movies`
- Download client category: `radarr`

## Sonarr

- URL: `http://192.168.1.197:8989`
- API key: store outside this repo
- Root folder: `/data/library/tv`
- Download client category: `sonarr`

## Prowlarr

- URL: `http://192.168.1.197:9696`
- API key: store outside this repo
- Indexer credentials: store outside this repo
- Network path after VPN activation: through Gluetun in CT `106`
- Only configure lawful/public-domain/owned-media sources.

## qBittorrent

- URL: `http://192.168.1.197:8080`
- Initial password: read from container logs after first start, then change it
- Categories:
  - `radarr` -> `/data/downloads/complete/radarr`
  - `sonarr` -> `/data/downloads/complete/sonarr`
- Incomplete downloads: `/data/downloads/incomplete`
- Network path after VPN activation: through Gluetun in CT `106`
- VPN forwarded port: store outside this repo and set the same value in qBittorrent

## Tailscale

- Subnet router: CT `107`, hostname `remote-access`
- Advertised route: `192.168.1.0/24`
- Tailscale account and device approval: store outside this repo
- Disable key expiry for CT `107` in the Tailscale admin console

## Commercial VPN

- Runtime env file: `/opt/media-stack/vpn.env` inside CT `106`
- Template: `media-stack/vpn.env.example`
- Recommended provider default: AirVPN with WireGuard and a forwarded port
- Store provider account, WireGuard private key, preshared key, assigned tunnel address, server choice, and forwarded port outside this repo
