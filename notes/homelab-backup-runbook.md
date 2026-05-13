# Homelab Backup Runbook

Last updated: 2026-05-12 22:53 CDT

## USB Backup Storage

- Device observed during setup: `/dev/sda`, USB model `Portable`, serial `NT3FY7HT`
- Filesystem: ext4, label `HOMELAB_BACKUP`
- Filesystem UUID: `9218d3f8-9449-4221-9dd8-36b5b7884152`
- Mountpoint: `/mnt/proxmox-usb-backup`
- Proxmox storage ID: `usb-backup`
- Storage guardrail: `is_mountpoint 1`, so Proxmox should not write backups to the root disk if the USB drive is absent.

The `/etc/fstab` entry uses `nofail` so the host can boot if the USB disk is unplugged.

## Scheduled Backups

Proxmox job `homelab-usb-daily` runs daily at `02:30` and backs up all guests to `usb-backup` using snapshot mode and zstd compression.

Retention:

- 7 daily backups
- 4 weekly backups
- 3 monthly backups

The job uses `--all 1`, so it covers the current VM and LXC set, including stopped guests. Proxmox guest backups exclude host bind mounts such as `/srv/media-stack`, so shared media-stack data is covered by the separate file-backup timer below.

Host configuration is backed up separately by `homelab-host-backup.timer` at `01:15` daily. It writes root-only archives under:

```text
/mnt/proxmox-usb-backup/host-config/
```

Those archives include Proxmox host configuration, network/fstab/systemd configuration, cron configuration, and this repo. They may contain sensitive operational material because they are real host backups; do not copy them into Git.

Host bind-mounted data is backed up separately by `homelab-file-backup.timer` at `01:45` daily. It creates rsync hardlink snapshots for `/srv/media-stack` under:

```text
/mnt/proxmox-usb-backup/file-backups/srv-media-stack/
```

The `current` symlink points at the latest snapshot. Old snapshots are pruned after 120 days by default.

FileBrowser Quantum in CT `106` exposes only selected backup views:

- Proxmox guest backup archives from `/mnt/proxmox-usb-backup/dump`, mounted read-only at `/backups/guest-dumps`.
- The latest media-library backup, currently resolved from `/mnt/proxmox-usb-backup/file-backups/srv-media-stack/snapshots/20260512-015501/library`, mounted read-only at `/backups/media-library-current`.

These sources are intended for the FileBrowser admin account only. The root-only `host-config` archives are deliberately not mounted into FileBrowser because they may contain sensitive operational material.
Proxmox does not accept the `current` symlink as the bind-mount source, so refresh CT `106` `mp2` after a newer file-backup snapshot should be browsed.

## Useful Checks

```bash
findmnt /mnt/proxmox-usb-backup
pvesm status
pvesh get /cluster/backup --output-format yaml
systemctl list-timers homelab-host-backup.timer
systemctl list-timers homelab-file-backup.timer
systemctl status homelab-host-backup.service
systemctl status homelab-file-backup.service
ls -lh /mnt/proxmox-usb-backup/dump
ls -lh /mnt/proxmox-usb-backup/host-config
ls -lh /mnt/proxmox-usb-backup/file-backups/srv-media-stack
```

## Manual Backup Commands

Run the host-config backup immediately:

```bash
systemctl start homelab-host-backup.service
```

Run the host bind-mounted data backup immediately:

```bash
systemctl start homelab-file-backup.service
```

Run the Proxmox guest backup job immediately:

```bash
vzdump --all 1 --storage usb-backup --mode snapshot --compress zstd --prune-backups keep-daily=7,keep-weekly=4,keep-monthly=3
```

## Restore Notes

- Restore VM/LXC guests from the Proxmox UI or `qmrestore`/`pct restore` using archives in `/mnt/proxmox-usb-backup/dump`.
- Restore host configuration selectively from the latest `host-config/proxmox-host-config.*.tar.zst` archive.
- Restore shared media-stack data from `file-backups/srv-media-stack/current`.
- Recreate the USB mount and `usb-backup` storage before relying on scheduled backups after a host rebuild.
- Do not restore `/etc/pve/priv` material onto a different trust boundary without understanding the security impact.
