#!/usr/bin/env bash
set -euo pipefail

BACKUP_MOUNT="${BACKUP_MOUNT:-/mnt/proxmox-usb-backup}"
BACKUP_DIR="${BACKUP_DIR:-${BACKUP_MOUNT}/albumary-sqlite}"
KEEP_DAYS="${KEEP_DAYS:-30}"
VMID="${ALBUMARY_VMID:-105}"
DB_PATH="${ALBUMARY_DB_PATH:-/opt/spotify_tracker/data/spotify_tracker.sqlite}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BASENAME="albumary-sqlite.${STAMP}.sqlite"
CT_TMP="/tmp/${BASENAME}"
PARTIAL_DB="${BACKUP_DIR}/.${BASENAME}.partial"
ARCHIVE="${BACKUP_DIR}/${BASENAME}.gz"

cleanup() {
  rm -f "${PARTIAL_DB}"
  pct exec "${VMID}" -- rm -f "${CT_TMP}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

if ! mountpoint -q "${BACKUP_MOUNT}"; then
  echo "Backup mount ${BACKUP_MOUNT} is not mounted" >&2
  exit 1
fi

if ! pct status "${VMID}" | grep -q '^status: running$'; then
  echo "Container ${VMID} is not running" >&2
  exit 1
fi

if ! pct exec "${VMID}" -- test -r "${DB_PATH}"; then
  echo "Albumary database ${DB_PATH} is not readable in CT ${VMID}" >&2
  exit 1
fi

if ! command -v sqlite3 >/dev/null; then
  echo "sqlite3 is not installed on the Proxmox host" >&2
  exit 1
fi

mkdir -p "${BACKUP_DIR}"

pct exec "${VMID}" -- sqlite3 "${DB_PATH}" ".backup ${CT_TMP}"
pct exec "${VMID}" -- sqlite3 "${CT_TMP}" "PRAGMA integrity_check;" | grep -qx 'ok'

pct pull "${VMID}" "${CT_TMP}" "${PARTIAL_DB}" --perms 0600 --user root --group root
sqlite3 "${PARTIAL_DB}" "PRAGMA integrity_check;" | grep -qx 'ok'

gzip -n -9 <"${PARTIAL_DB}" >"${ARCHIVE}"
chmod 0600 "${ARCHIVE}"
rm -f "${PARTIAL_DB}"
pct exec "${VMID}" -- rm -f "${CT_TMP}"
trap - EXIT

find "${BACKUP_DIR}" \
  -type f \
  -name 'albumary-sqlite.*.sqlite.gz' \
  -mtime "+${KEEP_DAYS}" \
  -delete

echo "Created ${ARCHIVE}"
