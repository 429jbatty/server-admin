---
name: homelab-pve-lenovo
description: Interact safely with the existing Lenovo Proxmox production and migration-source host from `/root/server-admin`. Use when inspecting or changing the Lenovo host, running Proxmox, LVM, storage, backup, or migration-preparation work.
---

# Homelab PVE Lenovo

Use this skill for work on the existing Lenovo Proxmox host, especially while it remains the production migration source.

## Identity And Role

- Repo path: `/root/server-admin`
- Last-known hostname: `proxmox`
- Last-known LAN address: `192.168.1.184`
- Role during migration: live production/source host
- Backup HDD mountpoint: `/mnt/proxmox-usb-backup`
- Backup HDD filesystem UUID: `9218d3f8-9449-4221-9dd8-36b5b7884152`
- Proxmox backup storage ID: `usb-backup`

Reverify live state before acting. After cutover, do not assume this host is still authoritative.

## Start Protocol

1. Read `/root/server-admin/AGENTS.md`, `README.md`, and the relevant runbook.
2. For migration work, also read `notes/migrations/lenovo-to-nuc/README.md` and the relevant phase doc.
3. Run `git status --short`.
4. Ask what the user changed manually since the last session.
5. Verify live state with read-only host checks before changes.
6. Summarize docs/live-state mismatches before acting.
7. Update operational docs and the migration cutover log after verified work.

## Restricted-Shell Quirk

This environment may run ordinary commands in a restricted mount and permission namespace.

- Non-escalated `findmnt` previously reported `/mnt/proxmox-usb-backup` as read-only even while the real host mount was `rw,noatime`.
- Non-escalated `pvesm`, `pct`, `qm`, `vgs`, and `lvs` may fail with permission, syslog, IPC, or file-locking errors.
- Treat those failures and restricted-namespace mount results as environment artifacts until checked in the real host namespace.
- Use the required host-level escalation for authoritative Proxmox, LVM, process, journal, and mount checks.
- Do not repeatedly retry the same Proxmox/LVM command without escalation after a characteristic sandbox failure.

Authoritative mount verification pattern:

```bash
findmnt /mnt/proxmox-usb-backup -o TARGET,SOURCE,FSTYPE,OPTIONS
grep /mnt/proxmox-usb-backup /proc/mounts
df -h /mnt/proxmox-usb-backup
```

Run these in the host namespace when making operational decisions.

## Safe Read-Only Baseline

Use the relevant subset:

```bash
hostnamectl
pveversion -v
git -C /root/server-admin status --short
pvesm status
qm list
pct list
findmnt /mnt/proxmox-usb-backup -o TARGET,SOURCE,FSTYPE,OPTIONS
lsblk -f
lsusb
vgs
lvs -a -o lv_name,vg_name,lv_size,data_percent,metadata_percent,origin,pool_lv,lv_attr
```

For guest work, verify the specific guest before acting:

```bash
pct status <ctid>
pct config <ctid>
qm status <vmid>
qm config <vmid>
```

## Lenovo-Specific Guardrails

- Treat the host as production until the user explicitly confirms cutover.
- Keep the Lenovo available until backups and NUC validation are complete.
- Never unplug or unmount the USB HDD while backup jobs, guest access, or media services are using it.
- Before deleting failed backup artifacts, verify no `vzdump`, `tar`, or `zstd` process is active and no relevant Proxmox snapshot remains.
- A failed `vzdump` can leave a snapshot named `vzdump` and a `.tmp` directory. Inspect first; clean only the verified leftovers.
- Thin-pool virtual-size warnings are not by themselves proof of failure. Check actual `data_percent`, metadata usage, free VG space, and task logs.
- Distinguish normal read-only mounting of guest snapshot filesystems during `vzdump` from the backup HDD mount becoming read-only.
- Use the host kernel journal and host-namespace mount view before diagnosing USB or ext4 failure.
- Never format, repartition, or erase the backup HDD.
- Never commit raw inventory, backup archives, secrets, databases, private keys, or `/etc/pve/priv/*`.

## Backup Recovery Pattern

When a guest backup fails:

1. Check the Proxmox task log and identify where it failed.
2. Verify the guest remains healthy.
3. Verify no backup process is active.
4. Check `pct listsnapshot <ctid>` or the VM equivalent.
5. Check LVM snapshot state when applicable.
6. Verify the real host mount options for `usb-backup`.
7. Remove only confirmed stale snapshots or incomplete temporary artifacts.
8. Retry the single guest first.
9. Verify archive visibility, compression integrity, snapshot cleanup, and guest status.
10. Record the result in the migration cutover log.

## Documentation

Keep these aligned with verified changes:

- `/root/server-admin/notes/migrations/lenovo-to-nuc/cutover-log.md`
- `/root/server-admin/notes/proxmox-media-inventory.md`
- `/root/server-admin/notes/homelab-backup-runbook.md`
- Other affected runbooks and `homelab-services.yml`

Use live state as current truth only after authoritative read-only verification.
