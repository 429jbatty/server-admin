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
- Only configure lawful/public-domain/owned-media sources.

## qBittorrent

- URL: `http://192.168.1.197:8080`
- Initial password: read from container logs after first start, then change it
- Categories:
  - `radarr` -> `/data/downloads/complete/radarr`
  - `sonarr` -> `/data/downloads/complete/sonarr`
- Incomplete downloads: `/data/downloads/incomplete`

## VPN or Usenet

Not configured in the initial lightweight build. If added later, store provider details outside this repo and update the runbook with non-secret configuration only.
