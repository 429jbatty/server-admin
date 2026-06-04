# Phase 4: Storage And Devices

Goal: make the NUC storage and passthrough devices match what the restored guests expect.

## Agent Rules

- Start with read-only checks.
- Do not repartition, format, or erase disks unless the user explicitly asks for that specific action.
- If a device path differs on the NUC, verify by stable ID before changing guest configs.
- Back up guest configs before changing mount points, device passthrough, or resources.

## USB HDD

Expected first-pass USB HDD identity:

```text
label: HOMELAB_BACKUP
filesystem UUID: 9218d3f8-9449-4221-9dd8-36b5b7884152
mountpoint: /mnt/proxmox-usb-backup
Proxmox storage ID: usb-backup
```

Expected folders:

```text
/mnt/proxmox-usb-backup/dump
/mnt/proxmox-usb-backup/host-config
/mnt/proxmox-usb-backup/file-backups
/mnt/proxmox-usb-backup/albumary-sqlite
/mnt/proxmox-usb-backup/media-stack
```

Read-only checks:

```bash
lsblk -f
blkid
findmnt /mnt/proxmox-usb-backup
pvesm status
cat /etc/pve/storage.cfg
ls -la /mnt/proxmox-usb-backup
```

## Bind Mounts Expected By Guests

CT `104` active Jellyfin:

```text
/mnt/proxmox-usb-backup/media-stack -> /media
```

CT `106` media stack:

```text
/mnt/proxmox-usb-backup/media-stack -> /data
/mnt/proxmox-usb-backup/dump -> /backups/guest-dumps read-only
/mnt/proxmox-usb-backup/file-backups/srv-media-stack/snapshots/<resolved-snapshot>/library -> /backups/media-library-current read-only
```

The `media-library-current` mount uses a resolved snapshot path because Proxmox does not hotplug bind mounts through the `current` symlink.

## Device Checks

SONOFF Zigbee coordinator for Home Assistant VM `100`:

```text
USB ID: 10c4:ea60
host device type: Silicon Labs CP210x UART Bridge
VM config: usb0: host=10c4:ea60
inside VM: /dev/ttyUSB0
```

Read-only checks:

```bash
lsusb
ls -la /dev/serial/by-id/ 2>/dev/null
qm config 100
```

Intel iGPU for Jellyfin CT `104`:

```bash
ls -la /dev/dri
pct config 104
```

Expected Lenovo-era paths were `/dev/dri/renderD128` and `/dev/dri/card1`. Reverify on the NUC before reusing those exact paths.

TUN device for CT `106` Gluetun and CT `107` Tailscale:

```bash
ls -la /dev/net/tun
pct config 106
pct config 107
```

USB Ethernet or NUC NIC bridge:

```bash
ip link
cat /etc/network/interfaces
```

The Lenovo bridge used `enx00051b93a9d0`. The NUC interface name will likely differ; verify bridge membership on the NUC.

## Completion Criteria

- USB HDD is mounted at `/mnt/proxmox-usb-backup`.
- `usb-backup` storage is active and guarded by `is_mountpoint 1`.
- Required media and backup directories are present.
- Zigbee USB device is visible before starting Home Assistant.
- Intel iGPU device paths are verified before starting Jellyfin.
- `/dev/net/tun` is available before starting CT `106` and CT `107`.
- Network bridge uses the correct NUC interface.
