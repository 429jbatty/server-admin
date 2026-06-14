#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${STATE_DIR:-/var/lib/homelab-health-watchdog}"
LOG_ROOT="${LOG_ROOT:-/var/log/homelab-health-watchdog}"
FAILURE_FILE="${STATE_DIR}/consecutive-failures"
LOCK_FILE="${STATE_DIR}/run.lock"
FAILURE_THRESHOLD="${FAILURE_THRESHOLD:-3}"
REBOOT_COMMAND="${REBOOT_COMMAND:-systemctl reboot}"
DRY_RUN="${DRY_RUN:-0}"
CHECK_GATEWAY="${CHECK_GATEWAY:-0}"
GATEWAY="${GATEWAY:-192.168.1.1}"
CRITICAL_SERVICES="${CRITICAL_SERVICES:-pve-cluster pvedaemon pveproxy pvestatd pvescheduler pve-guests watchdog-mux ssh}"

mkdir -p "${STATE_DIR}" "${LOG_ROOT}"
chmod 0750 "${STATE_DIR}" "${LOG_ROOT}"

exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
  echo "Another homelab-health-watchdog run is already active" >&2
  exit 0
fi

run_capture() {
  local output_file="$1"
  shift

  {
    printf '$'
    printf ' %q' "$@"
    printf '\n'
    "$@"
  } >"${output_file}" 2>&1 || true
}

collect_diagnostics() {
  local reason="$1"
  local stamp
  local diag_dir

  stamp="$(date +%Y%m%d-%H%M%S)"
  diag_dir="${LOG_ROOT}/${stamp}"
  mkdir -p "${diag_dir}"
  chmod 0750 "${diag_dir}"

  {
    echo "timestamp=$(date --iso-8601=seconds)"
    echo "hostname=$(hostname -f 2>/dev/null || hostname)"
    echo "kernel=$(uname -a)"
    echo "reason=${reason}"
    echo "consecutive_failures=$(cat "${FAILURE_FILE}" 2>/dev/null || echo 0)"
    echo "failure_threshold=${FAILURE_THRESHOLD}"
    echo "dry_run=${DRY_RUN}"
    echo "critical_services=${CRITICAL_SERVICES}"
    echo "check_gateway=${CHECK_GATEWAY}"
    echo "gateway=${GATEWAY}"
  } >"${diag_dir}/summary.env"

  journalctl -b --no-pager >"${diag_dir}/journal-current-boot.log" 2>&1 || true
  dmesg -T >"${diag_dir}/dmesg.log" 2>&1 || true

  for service in ${CRITICAL_SERVICES}; do
    systemctl status "${service}" --no-pager >"${diag_dir}/systemctl-${service}.log" 2>&1 || true
    journalctl -b -u "${service}" --no-pager >"${diag_dir}/journal-${service}.log" 2>&1 || true
  done

  run_capture "${diag_dir}/systemctl-failed.log" systemctl --failed --no-pager
  run_capture "${diag_dir}/systemctl-list-units.log" systemctl list-units --no-pager
  run_capture "${diag_dir}/systemctl-list-timers.log" systemctl list-timers --all --no-pager
  run_capture "${diag_dir}/pct-list.log" pct list
  run_capture "${diag_dir}/qm-list.log" qm list
  run_capture "${diag_dir}/pvesm-status.log" pvesm status
  run_capture "${diag_dir}/df-h.log" df -h
  run_capture "${diag_dir}/findmnt.log" findmnt
  run_capture "${diag_dir}/ip-address.log" ip addr show
  run_capture "${diag_dir}/ip-route.log" ip route show
  run_capture "${diag_dir}/free.log" free -h
  run_capture "${diag_dir}/uptime.log" uptime
  run_capture "${diag_dir}/processes.log" ps auxww

  find "${LOG_ROOT}" \
    -mindepth 1 \
    -maxdepth 1 \
    -type d \
    -mtime +30 \
    -exec rm -rf {} +

  echo "${diag_dir}"
}

check_health() {
  local failures=()
  local service

  for service in ${CRITICAL_SERVICES}; do
    if ! systemctl is-active --quiet "${service}"; then
      failures+=("service ${service} is not active")
    fi
  done

  if ! mountpoint -q /etc/pve; then
    failures+=("/etc/pve is not mounted")
  fi

  if ! timeout 20 pct list >/dev/null 2>&1; then
    failures+=("pct list failed or timed out")
  fi

  if ! timeout 20 qm list >/dev/null 2>&1; then
    failures+=("qm list failed or timed out")
  fi

  if ! timeout 20 pvesm status >/dev/null 2>&1; then
    failures+=("pvesm status failed or timed out")
  fi

  if command -v curl >/dev/null 2>&1; then
    if ! curl -kfsS --max-time 20 https://127.0.0.1:8006/ >/dev/null; then
      failures+=("local Proxmox web health request failed")
    fi
  fi

  if [[ "${CHECK_GATEWAY}" == "1" ]]; then
    if ! ping -c 1 -W 3 "${GATEWAY}" >/dev/null 2>&1; then
      failures+=("gateway ping failed for ${GATEWAY}")
    fi
  fi

  if ((${#failures[@]} > 0)); then
    printf '%s\n' "${failures[@]}"
    return 1
  fi

  return 0
}

current_failures="$(cat "${FAILURE_FILE}" 2>/dev/null || echo 0)"
if ! [[ "${current_failures}" =~ ^[0-9]+$ ]]; then
  current_failures=0
fi

failure_output="$(mktemp)"
trap 'rm -f "${failure_output}"' EXIT

if check_health >"${failure_output}" 2>&1; then
  echo 0 >"${FAILURE_FILE}"
  echo "Homelab health watchdog checks passed"
  exit 0
fi

next_failures=$((current_failures + 1))
echo "${next_failures}" >"${FAILURE_FILE}"

echo "Homelab health watchdog check failed (${next_failures}/${FAILURE_THRESHOLD}):" >&2
cat "${failure_output}" >&2

if ((next_failures < FAILURE_THRESHOLD)); then
  exit 1
fi

diag_dir="$(collect_diagnostics "$(tr '\n' '; ' <"${failure_output}")")"
echo "Saved homelab health watchdog diagnostics to ${diag_dir}" >&2

if [[ "${DRY_RUN}" == "1" ]]; then
  echo "DRY_RUN=1; skipping reboot command: ${REBOOT_COMMAND}" >&2
  exit 1
fi

logger -t homelab-health-watchdog "Rebooting after ${next_failures} consecutive failed health checks; diagnostics: ${diag_dir}"
sync
# shellcheck disable=SC2086
exec ${REBOOT_COMMAND}
