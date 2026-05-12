#!/usr/bin/env bash
set -euo pipefail

BACKUP_MOUNT="/mnt/proxmox-usb-backup"
SOURCE_DIR="/srv/media-stack/"
BACKUP_NAME="srv-media-stack"
BACKUP_ROOT="${BACKUP_MOUNT}/file-backups/${BACKUP_NAME}"
SNAPSHOT_ROOT="${BACKUP_ROOT}/snapshots"
CURRENT_LINK="${BACKUP_ROOT}/current"
KEEP_DAYS="${KEEP_DAYS:-120}"
STAMP="$(date +%Y%m%d-%H%M%S)"
PARTIAL_DIR="${BACKUP_ROOT}/.partial-${STAMP}"
SNAPSHOT_DIR="${SNAPSHOT_ROOT}/${STAMP}"

if ! mountpoint -q "${BACKUP_MOUNT}"; then
  echo "Backup mount ${BACKUP_MOUNT} is not mounted" >&2
  exit 1
fi

if [[ ! -d "${SOURCE_DIR}" ]]; then
  echo "Source directory ${SOURCE_DIR} does not exist" >&2
  exit 1
fi

mkdir -p "${SNAPSHOT_ROOT}"
rm -rf "${PARTIAL_DIR}"
mkdir -p "${PARTIAL_DIR}"
trap 'rm -rf "${PARTIAL_DIR}"' EXIT

rsync_args=(
  -aH
  --numeric-ids
  --delete
)

if [[ -e "${CURRENT_LINK}" ]]; then
  rsync_args+=(--link-dest="${CURRENT_LINK}")
fi

rsync "${rsync_args[@]}" "${SOURCE_DIR}" "${PARTIAL_DIR}/"

mv "${PARTIAL_DIR}" "${SNAPSHOT_DIR}"
trap - EXIT
ln -sfn "snapshots/${STAMP}" "${BACKUP_ROOT}/current.new"
mv -Tf "${BACKUP_ROOT}/current.new" "${CURRENT_LINK}"

find "${SNAPSHOT_ROOT}" \
  -mindepth 1 \
  -maxdepth 1 \
  -type d \
  -mtime "+${KEEP_DAYS}" \
  -exec rm -rf {} +

echo "Created ${SNAPSHOT_DIR}"
