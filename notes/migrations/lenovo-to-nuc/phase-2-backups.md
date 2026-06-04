# Phase 2: Backups

Goal: create and verify fresh backups before any cutover, restore, or hardware move.

## Agent Rules

- Start with read-only checks.
- Ask the user what backup work they already performed manually.
- If backup state is unclear, verify timestamps and file locations before running new backups.
- Do not copy real backup archives into Git.
- Do not expose contents of host-config backups in chat or docs; they may contain sensitive operational material.

## Read-Only Checks

```bash
git status --short
findmnt /mnt/proxmox-usb-backup
pvesm status
pvesh get /cluster/backup --output-format yaml
systemctl list-timers homelab-host-backup.timer
systemctl list-timers homelab-file-backup.timer
systemctl list-timers albumary-sqlite-backup.timer
ls -lh /mnt/proxmox-usb-backup/dump
ls -lh /mnt/proxmox-usb-backup/host-config
ls -lh /mnt/proxmox-usb-backup/file-backups/srv-media-stack
ls -lh /mnt/proxmox-usb-backup/albumary-sqlite
```

## Backup Commands

Run only when the user asks for backup execution.

Host configuration backup:

```bash
systemctl start homelab-host-backup.service
```

Host bind-mounted media-stack file backup:

```bash
systemctl start homelab-file-backup.service
```

Albumary database-only backup:

```bash
systemctl start albumary-sqlite-backup.service
```

Full Proxmox guest backup:

```bash
vzdump --all 1 --storage usb-backup --mode snapshot --compress zstd --prune-backups keep-daily=7,keep-weekly=4,keep-monthly=3
```

## Verification

After backups run, verify:

```bash
ls -lt /mnt/proxmox-usb-backup/dump | head
ls -lt /mnt/proxmox-usb-backup/host-config | head
ls -lt /mnt/proxmox-usb-backup/file-backups/srv-media-stack/snapshots | head
ls -lt /mnt/proxmox-usb-backup/albumary-sqlite | head
```

Expected fresh backup coverage:

- VM `100`: Home Assistant OS.
- CT `101`: stopped reference container.
- CT `102`: AdGuard Home.
- CT `103`: stale Jellyfin candidate.
- CT `104`: active Jellyfin.
- CT `105`: Albumary.
- CT `106`: media stack host.
- CT `107`: Tailscale subnet router.
- CT `108`: monitoring stack.
- Host config archive under `/mnt/proxmox-usb-backup/host-config`.
- Media-stack file snapshot under `/mnt/proxmox-usb-backup/file-backups/srv-media-stack`.
- Albumary SQLite backup under `/mnt/proxmox-usb-backup/albumary-sqlite`.

## Restore Readiness Notes

- Proxmox guest backups do not include host bind mounts such as `/mnt/proxmox-usb-backup/media-stack`.
- Media-stack app configs and library data are on the USB HDD under `/mnt/proxmox-usb-backup/media-stack`.
- File-backup snapshots are on the same physical USB HDD, so they are rollback snapshots, not an independent hardware backup.
- Home Assistant should also keep its own backup workflow enabled, including off-box sync.

## Completion Criteria

- The USB HDD is mounted and visible to Proxmox as `usb-backup`.
- Fresh guest backup archives exist for the migration scope.
- Fresh host-config, media-stack file, and Albumary SQLite backups exist.
- The user knows which backup set should be restored on the NUC.
