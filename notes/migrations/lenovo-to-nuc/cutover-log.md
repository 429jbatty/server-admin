# Lenovo To NUC Cutover Log

This file is agent-maintained by default. The user does not need to keep it current by hand.

Use it for concise notes after verified work or discovered mismatches. Do not store secrets, raw dumps, private keys, app databases, or backup archive contents here.

## Entry Format

```text
Date:
Actor:
Phase:
What was checked or changed:
Evidence:
Next safe action:
```

## Entries

Date: 2026-06-01
Actor: Agent
Phase: Phase 3 / Phase 4 preflight
What was checked or changed: Ran approved read-only SSH preflight against `pve-nuc`.
Evidence: NUC is reachable as hostname `pve-nuc` at `192.168.1.185/24`, running Proxmox VE `9.2.3` on Debian 13 with kernel `7.0.6-2-pve`. Storage currently has `local` and `local-lvm`; `usb-backup` is not configured. No VMs or LXCs are present. `/dev/dri/card0`, `/dev/dri/renderD128`, and `/dev/net/tun` exist. `/mnt/proxmox-usb-backup` is not mounted. `lsusb` shows a Logitech receiver and Intel Bluetooth, but not the Seagate USB HDD or SONOFF Zigbee coordinator.
Next safe action: Verify and create fresh Lenovo-side backups before moving the USB HDD or restoring guests.

Date: 2026-06-01
Actor: Agent
Phase: Phase 2 backup readiness
What was checked or changed: Ran approved read-only Lenovo-side backup readiness checks.
Evidence: `usb-backup` is active in Proxmox and the daily backup job `homelab-usb-daily` is enabled for all guests at `02:30`. VM `100` is running; CTs `102`, `104`, `105`, `106`, `107`, and `108` are running; CTs `101` and `103` are stopped. Latest visible guest backups, host-config backup, media-stack file snapshot, and Albumary SQLite backup are from 2026-05-31. The USB HDD is mounted at `/mnt/proxmox-usb-backup` but currently shows read-only mount options.
Next safe action: Diagnose why `/mnt/proxmox-usb-backup` is mounted read-only before running fresh migration backups.

Date: 2026-06-01
Actor: Agent
Phase: Phase 2 backup readiness
What was checked or changed: Ran approved read-only diagnostics for the read-only USB backup mount.
Evidence: `/etc/fstab` mounts UUID `9218d3f8-9449-4221-9dd8-36b5b7884152` at `/mnt/proxmox-usb-backup` with `defaults,noatime,nofail,x-systemd.device-timeout=10`, not an explicit read-only option. `/etc/pve/storage.cfg` defines `usb-backup` with `is_mountpoint 1`. `findmnt` still reports `/dev/sda1 ext4 ro,nosuid,nodev,noatime`, but `lsblk -f /dev/sda` reports `/dev/sda` is not a block device and `blkid /dev/sda1` returns no device data. Backup services last completed successfully on 2026-05-31. Recent kernel log output reviewed did not show an obvious ext4 remount error in the captured tail.
Next safe action: Confirm whether the USB HDD is physically connected to the Lenovo, inspect current block devices, and decide whether to remount/reconnect before running fresh backups.

Date: 2026-06-01
Actor: Agent
Phase: Phase 2 backup readiness
What was checked or changed: Rechecked physical USB HDD visibility after user confirmed it is plugged into the Lenovo.
Evidence: `lsblk -f` now shows `/dev/sda1` as ext4 label `HOMELAB_BACKUP`, UUID `9218d3f8-9449-4221-9dd8-36b5b7884152`, mounted at `/mnt/proxmox-usb-backup` with about 3.4T available. `lsusb` shows Seagate RSS LLC Portable device `0bc2:2344`. `findmnt` still shows the mount as read-only. `/dev/disk/by-uuid/` was not present in this shell environment.
Next safe action: Diagnose why the present ext4 filesystem is mounted read-only before running fresh migration backups.

Date: 2026-06-03
Actor: Agent
Phase: Phase 2 backup recovery and verification
What was checked or changed: Recovered from the failed CT `108` backup, removed its incomplete temporary backup directory, retried the CT-only snapshot backup, and verified Phase 2 backup readiness.
Evidence: Host-namespace checks confirmed `/dev/sda1` is mounted at `/mnt/proxmox-usb-backup` as `rw,noatime`; earlier read-only observations came from the restricted agent shell rather than the host mount namespace. The stale `vzdump` snapshot had already been removed and no backup process was active. The retry created `/mnt/proxmox-usb-backup/dump/vzdump-lxc-108-2026_06_03-22_52_11.tar.zst`, completed successfully, and passed `zstd -t`. `pct listsnapshot 108` shows only `current`. Proxmox lists fresh 2026-06-03 guest backups for VM `100` and CTs `101` through `108`; supporting host-config, media-stack file, and Albumary SQLite backups also exist from 2026-06-03.
Next safe action: Complete the reviewed Phase 3 NUC staging checks, confirm the planned cutover identity, and make the repo and host-level service sources available on the NUC before moving the USB HDD or restoring guests.

Date: 2026-06-03
Actor: Agent
Phase: Phase 3 NUC base install
What was checked or changed: Reverified the NUC staging host, installed required utilities, copied the clean server-admin repo from the Lenovo, and installed repo-backed host scripts and systemd units without enabling or starting them.
Evidence: `pve-nuc` remains reachable at staging address `192.168.1.185/24` with `vmbr0` bridged to `nic0`, Proxmox VE `9.2.3`, active `local` and `local-lvm` storage, and no guests. Installed `git`; `rsync` and `sqlite3` were already present. `/root/server-admin` is clean on branch `master` at commit `1574c88`. Backup scripts are installed under `/usr/local/sbin`; backup timers and the metrics exporter unit are installed under `/etc/systemd/system`. `systemd-analyze verify` passed, all newly installed units remain disabled and inactive, and `pveproxy` remains active. The USB HDD is not connected and `usb-backup` is intentionally not configured yet.
Next safe action: Complete final read-only Phase 3 reachability and host-capacity checks, keep the NUC on its staging identity while the Lenovo is live, then begin the reviewed Phase 4 physical storage and device move.
