# Homelab TODOs

This file tracks future work for the Proxmox home server. Keep operational details here when they are useful for planning, but keep secrets out of the repo.

## Backup And Restore

- USB backup target configured:
  - Storage ID: `usb-backup`
  - Mountpoint: `/mnt/proxmox-usb-backup`
  - Runbook: `notes/homelab-backup-runbook.md`
- Daily Proxmox backup job configured:
  - Job ID: `homelab-usb-daily`
  - Schedule: `02:30`
  - Scope: all guests
  - Retention: 7 daily, 4 weekly, 3 monthly
- Daily host configuration backup configured:
  - Timer: `homelab-host-backup.timer`
  - Schedule: `01:15`
  - Target: `/mnt/proxmox-usb-backup/host-config`
- Daily host bind-mount file backup configured:
  - Timer: `homelab-file-backup.timer`
  - Schedule: `01:45`
  - Target: `/mnt/proxmox-usb-backup/file-backups/srv-media-stack`
- Keep Home Assistant's own backup workflow enabled, including off-box sync.
- Test restores monthly.
  - Restore a small LXC to a new VMID.
  - Confirm the restored service boots and the expected LAN port responds.
  - Document the restore result in `notes/`.
- Create per-service restore notes for:
  - Home Assistant
  - AdGuard Home
  - Jellyfin
  - media stack services
  - Tailscale subnet router

## Proxmox Backup Server

- Consider adding Proxmox Backup Server on separate storage.
- Enable backup verification if PBS is added.
- Configure pruning and garbage collection on the datastore.
- Add notification routing for failed backup, verification, prune, or garbage-collection jobs.

## Git And Documentation

- Keep `/root/server-admin` as the Git source of truth for docs, desired configuration, scripts, service inventory, and non-secret templates.
- Commit after meaningful infrastructure changes.
- Push commits to the private remote after reviewing for secrets.
- Keep `homelab-services.yml` current when LAN IPs, ports, VMIDs, or dashboard services change.
- Keep `notes/proxmox-media-inventory.md` and service runbooks aligned with live Proxmox state.
- Add a simple secret-scan step before pushes.

## Data And Media

- Decide where the long-term media library should live before the library grows.
- Back up app configs and databases frequently.
- Back up the media library separately from VM/LXC backups.
- Do not back up incomplete downloads unless there is a clear reason.

## Security

- Do not commit API keys, passwords, VPN credentials, Tailscale auth keys, provider credentials, app databases, or Proxmox private keys.
- Do not commit `/etc/pve/priv/*`.
- Keep `.env.example` files in Git and real `.env` files out of Git.
- Keep services LAN-only unless a separate remote-access or reverse-proxy plan exists.
