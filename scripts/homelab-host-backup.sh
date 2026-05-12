#!/usr/bin/env bash
set -euo pipefail

BACKUP_MOUNT="/mnt/proxmox-usb-backup"
BACKUP_DIR="${BACKUP_MOUNT}/host-config"
KEEP_DAYS="${KEEP_DAYS:-120}"
STAMP="$(date +%Y%m%d-%H%M%S)"
ARCHIVE="${BACKUP_DIR}/proxmox-host-config.${STAMP}.tar.zst"

if ! mountpoint -q "${BACKUP_MOUNT}"; then
  echo "Backup mount ${BACKUP_MOUNT} is not mounted" >&2
  exit 1
fi

mkdir -p "${BACKUP_DIR}"

tar \
  --ignore-failed-read \
  --warning=no-file-changed \
  -I 'zstd -T0 -10' \
  -cf "${ARCHIVE}" \
  -C / \
  etc/pve \
  etc/network/interfaces \
  etc/hosts \
  etc/hostname \
  etc/fstab \
  etc/vzdump.conf \
  etc/cron.d \
  etc/systemd/system \
  root/server-admin

chmod 0600 "${ARCHIVE}"

find "${BACKUP_DIR}" \
  -type f \
  -name 'proxmox-host-config.*.tar.zst' \
  -mtime "+${KEEP_DAYS}" \
  -delete

echo "Created ${ARCHIVE}"
