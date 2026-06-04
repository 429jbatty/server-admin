# Phase 1: Inventory

Goal: collect enough read-only information from the Lenovo Proxmox host to safely migrate to the NUC.

Use the existing task file as the source of detailed inventory commands:

```text
../../../lenovo_proxmox_migration_inventory_task.md
```

## Agent Rules

- Inventory is read-only.
- Do not stop, restart, migrate, delete, upgrade, or reconfigure anything.
- Raw inventory output belongs outside Git.
- Only redacted, durable summaries belong in this repo.
- If live state differs from existing docs, summarize the mismatch before proposing changes.

## Raw Output Location

The inventory task should write raw output outside the repo:

```bash
/root/migration-inventory-$(date +%Y%m%d-%H%M%S)
/root/lenovo-migration-inventory-$(date +%Y%m%d-%H%M%S).tar.gz
```

Do not commit those paths or archives to Git.

## Read-Only Checks

Minimum checks before summarizing:

```bash
git status --short
pveversion -v
hostnamectl
cat /etc/network/interfaces
cat /etc/pve/storage.cfg
pvesm status
qm list
pct list
lsblk -f
findmnt /mnt/proxmox-usb-backup
lsusb
```

## Inventory script

There's a small read-only script you can run on the Lenovo host to collect the above outputs and archive them outside the repo:

`notes/migrations/lenovo-to-nuc/run-phase1-inventory.sh`

Run on the Lenovo host as root:

```bash
chmod +x /root/server-admin/notes/migrations/lenovo-to-nuc/run-phase1-inventory.sh
sudo /root/server-admin/notes/migrations/lenovo-to-nuc/run-phase1-inventory.sh
```

The script writes a timestamped directory under `/root` and a tar.gz archive alongside it. Do not commit those artifacts to Git.

## NUC prep notes

The NUC will keep the Lenovo USB HDD and the Zigbee coordinator attached. That means:

- Keep the USB HDD mounted on the NUC with the same or equivalent pathways used by the Lenovo host if possible.
- Do not configure the NUC to use the Lenovo internal disks; only use the NUC NVMe for the new Proxmox installation and local system storage.
- If you want the NUC to take the same static IP as the Lenovo (`192.168.1.185`), do that only after the Lenovo is powered off or disconnected from the LAN to avoid an IP conflict.

### Static IP and SSH on the NUC

Use the NUC console first to set a static IP and verify SSH is available before putting it on the network.

1. Confirm the Ethernet interface name:

```bash
ip link show
```

2. Set the static IP in `/etc/network/interfaces` on the NUC. Example using `vmbr0` and a physical interface `enp3s0` (replace with your actual interface name):

```bash
auto lo
iface lo inet loopback

auto enp3s0
iface enp3s0 inet manual

iface vmbr0 inet static
    address 192.168.1.185
    netmask 255.255.255.0
    gateway 192.168.1.1
    bridge_ports enp3s0
    bridge_stp off
    bridge_fd 0
```

3. If `openssh-server` is not installed, install it:

```bash
apt update
apt install -y openssh-server
```

4. Enable and start SSH:

```bash
systemctl enable ssh
systemctl start ssh
systemctl status ssh
```

5. Verify network and SSH from the NUC console:

```bash
ip a
ping -c 3 192.168.1.1
sshd -T | head
```

6. Once verified, connect the NUC to the LAN and test SSH from another machine:

```bash
ssh root@192.168.1.185
```

If you prefer to avoid IP conflict while both systems are temporarily on the network, assign a different static address to the NUC now and move the address to `192.168.1.185` after the Lenovo is offline.

For each guest, inspect config before making restore decisions:

```bash
qm config 100
pct config 101
pct config 102
pct config 103
pct config 104
pct config 105
pct config 106
pct config 107
pct config 108
```

## Redacted Summary To Preserve

After inventory, preserve these facts in a redacted summary or future doc update:

- Lenovo host identity, Proxmox version, CPU, RAM, storage, and network bridge.
- VM/LXC list with role, status, disk, memory, network, and restore priority.
- Any USB passthrough, PCI/device passthrough, bind mounts, privileged containers, Docker hosts, static IPs, static MACs, and unusual Proxmox config.
- Storage map including internal disks, USB HDD, filesystems, UUIDs, mountpoints, and services that depend on each path.
- Docker/Compose map for CT `106`, CT `108`, and any other discovered Docker hosts.
- Device map for the USB HDD, SONOFF Zigbee coordinator, USB Ethernet adapter, Intel iGPU, and `/dev/net/tun`.
- Git repo map for important local repos, remotes, and dirty worktrees.
- Backup inventory with latest backup archive per VM/CT and whether a fresh backup is needed.

## Expected Current Shape

Use live checks to confirm, but the current repo docs expect:

- VM `100`: Home Assistant OS.
- CT `102`: AdGuard Home.
- CT `103`: stale Jellyfin candidate; do not rely on it unless explicitly asked.
- CT `104`: active Jellyfin.
- CT `105`: Albumary.
- CT `106`: media stack Docker Compose host.
- CT `107`: Tailscale subnet router.
- CT `108`: monitoring stack.
- Shared media path: `/mnt/proxmox-usb-backup/media-stack`.
- Guest backup archives: `/mnt/proxmox-usb-backup/dump`.

## Completion Criteria

- Raw inventory folder and archive exist outside Git.
- `summary.md` and `migration-risks.md` from the raw inventory have been reviewed.
- Any migration blockers are copied into `risk-register.md` without secrets.
- The next phase can identify exactly which backup artifacts need to be freshened.
