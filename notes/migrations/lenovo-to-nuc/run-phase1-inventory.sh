#!/bin/bash
set -euo pipefail

# Read-only inventory script for the Lenovo Proxmox host.
# Run as root on the Lenovo host. It writes raw output to /root/lenovo-migration-inventory-<ts>

ts=$(date +%Y%m%d-%H%M%S)
outdir="/root/lenovo-migration-inventory-$ts"
mkdir -p "$outdir"
echo "Writing inventory to $outdir"

cmdout() {
  local name="$1"
  shift
  echo "--- $name ---" > "$outdir/$name.txt"
  "$@" >> "$outdir/$name.txt" 2>&1 || true
}

cmdout git-status git status --short
cmdout pveversion pveversion -v
cmdout hostnamectl hostnamectl
cmdout ip_a ip a
cmdout network_interfaces cat /etc/network/interfaces
cmdout pve_storage_cfg cat /etc/pve/storage.cfg
cmdout pvesm_status pvesm status
cmdout qm_list qm list
cmdout pct_list pct list
cmdout lsblk lsblk -f
cmdout blkid blkid
cmdout findmnt findmnt
cmdout findmnt_proxmox_usb findmnt /mnt/proxmox-usb-backup || true
cmdout lsusb lsusb
cmdout fstab cat /etc/fstab

# per-guest configs (write "missing" note if not present)
for id in 100 101 102 103 104 105 106 107 108; do
  if qm config "$id" >/dev/null 2>&1; then
    qm config "$id" > "$outdir/qm-$id.cfg" 2>&1 || true
  else
    echo "qm $id: missing or not defined" > "$outdir/qm-$id.cfg"
  fi
done

for id in 101 102 103 104 105 106 107 108; do
  if pct config "$id" >/dev/null 2>&1; then
    pct config "$id" > "$outdir/pct-$id.cfg" 2>&1 || true
  else
    echo "pct $id: missing or not defined" > "$outdir/pct-$id.cfg"
  fi
done

# create a compressed archive next to the folder (outside the repo)
tar -C /root -czf "/root/lenovo-migration-inventory-$ts.tar.gz" "$(basename "$outdir")" || true

echo "Inventory complete: $outdir"
echo "Archive: /root/lenovo-migration-inventory-$ts.tar.gz"

exit 0
