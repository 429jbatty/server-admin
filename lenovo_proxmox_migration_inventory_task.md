# Lenovo → NUC Proxmox Migration Inventory Task

## Goal

Collect enough information from the existing Lenovo Proxmox host to safely migrate everything to the new Intel NUC Proxmox host.

This is **inventory only**. Do not modify, stop, upgrade, delete, reboot, migrate, or reconfigure anything.

Write all output to:

```bash
/root/migration-inventory-$(date +%Y%m%d-%H%M%S)
```

Also create a compressed archive at the end:

```bash
/root/lenovo-migration-inventory-$(date +%Y%m%d-%H%M%S).tar.gz
```

---

## Core principles

1. **Read-only only.** No changes to running services.
2. **Prioritize migration blockers.** Identify anything that would fail if blindly restored on the NUC.
3. **Do not expose secrets.** List where secrets live, but do not copy token/password/private-key values.
4. **Capture dependencies.** Especially storage mounts, USB devices, static IPs, Docker volumes, bind mounts, and service order.
5. **Make the final output human-readable.** I need a concise migration summary, not a giant dump of logs.

---

## Collect these sections

### 1. Host and Proxmox overview

Capture:

```bash
pveversion -v
hostnamectl
lscpu
free -h
lsblk -f
df -h
pvesm status
cat /etc/pve/storage.cfg
cat /etc/network/interfaces
ip addr
ip route
```

Summarize:
- Lenovo hostname/IP
- Proxmox version
- CPU/RAM/storage
- Proxmox storage names and paths
- Network bridge/static IP config

---

### 2. VMs and LXCs

Capture:

```bash
qm list
pct list
```

For every VM:

```bash
qm config <VMID>
qm status <VMID> --verbose
```

For every LXC:

```bash
pct config <CTID>
pct status <CTID> --verbose
```

Summarize in tables:

```markdown
| ID | Type | Name | Role | Status | CPU | RAM | Disk | IP | Critical? | Restore Priority | Notes |
```

Flag anything with:
- USB passthrough
- PCI passthrough
- bind mounts / `mp0`, `mp1`, etc.
- Docker inside LXC/VM
- privileged LXC
- static MAC/IP
- external drive dependencies
- unusual Proxmox config

---

### 3. Storage and external drives

Identify:
- Internal disk layout
- External 4 TB drive, if present
- Mount points
- UUIDs
- Filesystems
- What services depend on each mount

Useful commands:

```bash
lsblk -f
blkid
mount
cat /etc/fstab
find /mnt /media /srv /opt -maxdepth 3 -type d 2>/dev/null
```

Summarize:

```markdown
| Device/UUID | Mount Point | Size | Filesystem | Used By | Migration Action |
```

---

### 4. Docker and app stacks

Find where Docker/Compose is running: host, VM, or LXC.

Capture where relevant:

```bash
docker ps -a
docker volume ls
docker network ls
find /root /home /opt /srv /mnt -name "docker-compose.yml" -o -name "compose.yml" 2>/dev/null
```

For compose files, make redacted copies or summarize them. Do not include secret values from `.env`.

Summarize:

```markdown
| Stack | Runs In | Compose Path | Config Path | Data Path | Ports | Depends On |
```

Pay special attention to:
- Home Assistant
- AdGuard
- Jellyfin
- Radarr
- Sonarr
- Prowlarr
- qBittorrent
- Jellyseerr
- Tailscale
- personal websites/apps

---

### 5. USB/device dependencies

Capture:

```bash
lsusb
lsusb -t
ls -la /dev/serial/by-id/ 2>/dev/null
lspci
```

Summarize:

```markdown
| Device | Stable ID/Path | Used By | Migration Concern |
```

Especially look for:
- Zigbee coordinator
- RTL-SDR
- external HDD
- UPS
- Bluetooth devices
- Coral/accelerator devices

---

### 6. Git repos and documentation

Find important local repos/docs:

```bash
find /root /home /opt /srv /mnt -type d -name ".git" 2>/dev/null
```

For each repo, summarize:
- path
- purpose
- remote URL
- dirty/uncommitted changes?
- important README/docs/compose files
- whether it must be copied, pushed, or recreated on the NUC

Do not dump full repo contents unless necessary.

---

### 7. Backups

Inventory existing backups only:

```bash
find /var/lib/vz/dump /mnt /media /srv -type f -name "vzdump-*" 2>/dev/null
```

Summarize:

```markdown
| VM/CT ID | Name | Latest Backup | Storage Location | Needs Fresh Backup? |
```

Do not create backups yet unless explicitly told.

---

## Required final outputs

Create these files:

```text
summary.md
vm-lxc-inventory.md
storage-map.md
docker-app-map.md
device-map.md
git-repo-map.md
backup-inventory.md
migration-risks.md
```

The most important file is:

```text
summary.md
```

It should answer:

1. What is running on the Lenovo?
2. What order should services be restored in?
3. What storage/mounts must exist on the NUC first?
4. What USB devices must move?
5. What static IPs or DNS dependencies matter?
6. Which apps use Docker/Compose and where are their configs/data?
7. Which repos/docs need to be preserved?
8. What are the biggest migration risks?

---

## Final response needed from agent

Return:

```text
Inventory folder path:
Archive path:
Contents of summary.md:
Contents of migration-risks.md:
Any recommended next steps before backup/restore:
```

Do not perform the migration.
