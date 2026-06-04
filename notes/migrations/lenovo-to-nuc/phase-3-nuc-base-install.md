# Phase 3: NUC Base Install

Goal: prepare the Intel NUC as a Proxmox host that can receive the Lenovo guests and existing USB HDD.

## Agent Rules

- Verify whether commands are running on the Lenovo or the NUC before acting.
- Do not overwrite an active host identity unless the user explicitly confirms the cutover moment.
- Keep the Lenovo available until backups and NUC readiness are verified.
- Prefer read-only checks before editing network, storage, or systemd configuration.

## Target Host Identity

Default first-pass target:

```text
hostname: proxmox
address: 192.168.1.184/24
gateway: 192.168.1.254
bridge: vmbr0
repo path: /root/server-admin
```

If the NUC temporarily uses a different IP during staging, record that in the session chat and verify before changing docs.

## Base Install Checklist

1. Install Proxmox on the NUC internal storage.
2. Configure `vmbr0` for the final or staging LAN address.
3. Confirm the Proxmox UI is reachable on the chosen address.
4. Install basic packages required by the runbooks, scripts, and backup checks.
5. Clone or restore `/root/server-admin`.
6. Verify the repo is on the expected branch and has no unexpected dirty files.
7. Recreate or restore host-level systemd units and scripts from this repo.

## Read-Only Checks

```bash
hostnamectl
pveversion -v
cat /etc/network/interfaces
ip addr
ip route
pvesm status
cat /etc/pve/storage.cfg
git -C /root/server-admin status --short
```

## Storage IDs To Recreate

The migration expects these Proxmox storage IDs by the end of Phase 4:

```text
local      dir storage at /var/lib/vz
local-lvm  lvmthin storage for VM/LXC disks
usb-backup dir storage at /mnt/proxmox-usb-backup with is_mountpoint 1
```

During Phase 3, verify `local` and `local-lvm`. Defer creating `usb-backup` until Phase 4, after the physical USB HDD has moved to the NUC and its filesystem UUID and mountpoint have been verified.

The `usb-backup` storage must not be active against an unmounted empty directory. Keep `is_mountpoint 1`.

## Host-Level Services To Restore Or Reinstall

From repo sources:

- `systemd/homelab-host-backup.service`
- `systemd/homelab-host-backup.timer`
- `systemd/homelab-file-backup.service`
- `systemd/homelab-file-backup.timer`
- `systemd/albumary-sqlite-backup.service`
- `systemd/albumary-sqlite-backup.timer`
- `systemd/homelab-metrics-exporter.service`
- `scripts/homelab-host-backup.sh`
- `scripts/homelab-file-backup.sh`
- `scripts/albumary-sqlite-backup.sh`
- `scripts/homelab-metrics-exporter.py`

## Completion Criteria

- NUC Proxmox UI is reachable.
- Host network identity is confirmed.
- Repo exists at `/root/server-admin`.
- `local` and `local-lvm` are active; `usb-backup` is explicitly deferred to Phase 4 until the HDD is mounted.
- Host-level service sources are available for installation.
- No guest restore has started before storage and device readiness are checked.
