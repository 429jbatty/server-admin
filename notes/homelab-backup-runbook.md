# Homelab Backup Runbook

Last updated: 2026-06-14 11:12 CDT

The active host is NUC node `pve-nuc`. From the retired Lenovo workspace, run active-host commands through `ssh pve-nuc`.

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

The job and all host backup timers are active on NUC node `pve-nuc` at `192.168.1.184`. The retired Lenovo source at `192.168.1.186` has its guest backup job and host backup timers disabled.

Retention:

- 7 daily backups
- 4 weekly backups
- 3 monthly backups

The job uses `--all 1`, so it covers the current VM and LXC set, including stopped guests. Proxmox guest backups exclude host bind mounts such as `/mnt/proxmox-usb-backup/media-stack`, so shared media-stack data is covered by the separate file-backup timer below.

Host configuration is backed up separately by `homelab-host-backup.timer` at `01:15` daily. It writes root-only archives under:

```text
/mnt/proxmox-usb-backup/host-config/
```

Those archives include Proxmox host configuration, network/fstab/systemd configuration, cron configuration, and this repo. They may contain sensitive operational material because they are real host backups; do not copy them into Git.

Host bind-mounted data is backed up separately by `homelab-file-backup.timer` at `01:45` daily. It creates rsync hardlink snapshots for `/mnt/proxmox-usb-backup/media-stack` under:

```text
/mnt/proxmox-usb-backup/file-backups/srv-media-stack/
```

The `srv-media-stack` backup directory name is historical. The current source path is `/mnt/proxmox-usb-backup/media-stack`. The `current` symlink points at the latest snapshot. Old snapshots are pruned after 120 days by default.

Albumary's SQLite database is backed up separately by `albumary-sqlite-backup.timer` at `02:05` daily, before the full Proxmox guest backup. Albumary runs in CT `105`, and the active database is:

```text
/opt/spotify_tracker/data/spotify_tracker.sqlite
```

The backup script uses SQLite's `.backup` command inside CT `105`, verifies the copy with `PRAGMA integrity_check`, pulls the copy to the host, verifies it again, then writes compressed database-only backups under:

```text
/mnt/proxmox-usb-backup/albumary-sqlite/
```

Albumary database-only backups are kept for 30 days by default. These backups make single-service recovery easier, but they live on the same USB disk as the Proxmox guest backups and are not a separate off-machine disaster backup.

FileBrowser Quantum in CT `106` exposes only selected backup views:

- Proxmox guest backup archives from `/mnt/proxmox-usb-backup/dump`, mounted read-only at `/backups/guest-dumps`.
- The media-library backup currently exposed to FileBrowser is resolved from `/mnt/proxmox-usb-backup/file-backups/srv-media-stack/snapshots/20260603-015205/library`, mounted read-only at `/backups/media-library-current`.

These sources are intended for the FileBrowser admin account only. The root-only `host-config` archives are deliberately not mounted into FileBrowser because they may contain sensitive operational material.
Proxmox does not accept the `current` symlink as the bind-mount source, so refresh CT `106` `mp2` after a newer file-backup snapshot should be browsed.

## Useful Checks

```bash
findmnt /mnt/proxmox-usb-backup
pvesm status
pvesh get /cluster/backup --output-format yaml
systemctl list-timers homelab-host-backup.timer
systemctl list-timers homelab-file-backup.timer
systemctl list-timers albumary-sqlite-backup.timer
systemctl list-timers homelab-health-watchdog.timer
systemctl status homelab-host-backup.service
systemctl status homelab-file-backup.service
systemctl status albumary-sqlite-backup.service
systemctl status homelab-health-watchdog.service
ls -lh /mnt/proxmox-usb-backup/dump
ls -lh /mnt/proxmox-usb-backup/host-config
ls -lh /mnt/proxmox-usb-backup/file-backups/srv-media-stack
ls -lh /mnt/proxmox-usb-backup/albumary-sqlite
ls -lh /var/log/homelab-health-watchdog
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

Run the Albumary database-only backup immediately:

```bash
systemctl start albumary-sqlite-backup.service
```

Run the Proxmox guest backup job immediately:

```bash
vzdump --all 1 --storage usb-backup --mode snapshot --compress zstd --prune-backups keep-daily=7,keep-weekly=4,keep-monthly=3
```

## Restore Notes

- Restore VM/LXC guests from the Proxmox UI or `qmrestore`/`pct restore` using archives in `/mnt/proxmox-usb-backup/dump`.
- Restore host configuration selectively from the latest `host-config/proxmox-host-config.*.tar.zst` archive.
- Restore shared media-stack data from `file-backups/srv-media-stack/current`.
- Restore Albumary's database by decompressing a selected `albumary-sqlite.*.sqlite.gz` backup, stopping `spotify-tracker-api.service` in CT `105`, replacing `/opt/spotify_tracker/data/spotify_tracker.sqlite`, fixing ownership to `jacob:jacob`, then starting the service again.
- Recreate the USB mount and `usb-backup` storage before relying on scheduled backups after a host rebuild.
- Do not restore `/etc/pve/priv` material onto a different trust boundary without understanding the security impact.

## Resilience Rollback Notes

Timestamped pre-change config backups for the June 7, 2026 resilience update
were saved on `pve-nuc` under `/root/server-admin/backups/`:

- `100.conf.20260607-171541.pre-resilience`
- `102.conf.20260607-171541.pre-resilience`
- `104.conf.20260607-171541.pre-resilience`
- `105.conf.20260607-171541.pre-resilience`
- `106.conf.20260607-171541.pre-resilience`
- `107.conf.20260607-171541.pre-resilience`
- `108.conf.20260607-171541.pre-resilience`
- `pve-ha-manager.default.20260607-171541.pre-resilience`

To roll back startup ordering, compare one of those guest config backups with the
live config under `/etc/pve/qemu-server/` or `/etc/pve/lxc/`, then revert only
the `startup:` line or use `qm set`/`pct set` with the previous startup value.

To roll back hardware watchdog selection, restore the previous
`/etc/default/pve-ha-manager` content or comment out `WATCHDOG_MODULE=wdat_wdt`.
Do not stop or restart `watchdog-mux` casually; Proxmox uses it for fencing and
the service can reset the host if mishandled. Prefer validating watchdog changes
during a planned reboot window.

The local `homelab-health-watchdog.timer` is separate from Proxmox
`watchdog-mux`. It does not use `/dev/watchdog`; it checks local Proxmox health,
gateway reachability, outbound HTTPS reachability, and recent `e1000e` NIC-hang
kernel logs every 5 minutes. On the second consecutive network-related failure
it saves diagnostics and bounces `nic0`; after 3 consecutive failures it saves
diagnostics and calls `systemctl reboot`.
Before disabling it for troubleshooting, capture its state:

```bash
systemctl list-timers homelab-health-watchdog.timer
systemctl status homelab-health-watchdog.service
cat /var/lib/homelab-health-watchdog/consecutive-failures
ls -lh /var/log/homelab-health-watchdog
```

To test the script without allowing a reboot:

```bash
DRY_RUN=1 /usr/local/sbin/homelab-health-watchdog
```

Pre-reboot diagnostics stored under `/var/log/homelab-health-watchdog/` may
contain sensitive host operational details from journals and process listings.
Keep them local and do not copy them into Git.
