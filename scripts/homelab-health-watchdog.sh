#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${STATE_DIR:-/var/lib/homelab-health-watchdog}"
LOG_ROOT="${LOG_ROOT:-/var/log/homelab-health-watchdog}"
FAILURE_FILE="${STATE_DIR}/consecutive-failures"
LOCK_FILE="${STATE_DIR}/run.lock"
FAILURE_THRESHOLD="${FAILURE_THRESHOLD:-3}"
REBOOT_COMMAND="${REBOOT_COMMAND:-systemctl reboot}"
DRY_RUN="${DRY_RUN:-0}"
CHECK_GATEWAY="${CHECK_GATEWAY:-1}"
GATEWAY="${GATEWAY:-192.168.1.254}"
CHECK_OUTBOUND="${CHECK_OUTBOUND:-1}"
OUTBOUND_URL="${OUTBOUND_URL:-https://cloudflare.com/cdn-cgi/trace}"
CHECK_KERNEL_NIC_HANG="${CHECK_KERNEL_NIC_HANG:-1}"
KERNEL_NIC_HANG_LOOKBACK="${KERNEL_NIC_HANG_LOOKBACK:--10min}"
NETWORK_INTERFACE="${NETWORK_INTERFACE:-nic0}"
ENABLE_NIC_RECOVERY="${ENABLE_NIC_RECOVERY:-1}"
NIC_RECOVERY_FAILURE_COUNT="${NIC_RECOVERY_FAILURE_COUNT:-2}"
NIC_RECOVERY_DOWN_SECONDS="${NIC_RECOVERY_DOWN_SECONDS:-5}"
NIC_RECOVERY_SETTLE_SECONDS="${NIC_RECOVERY_SETTLE_SECONDS:-20}"
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
    echo "check_outbound=${CHECK_OUTBOUND}"
    echo "outbound_url=${OUTBOUND_URL}"
    echo "check_kernel_nic_hang=${CHECK_KERNEL_NIC_HANG}"
    echo "kernel_nic_hang_lookback=${KERNEL_NIC_HANG_LOOKBACK}"
    echo "network_interface=${NETWORK_INTERFACE}"
    echo "enable_nic_recovery=${ENABLE_NIC_RECOVERY}"
    echo "nic_recovery_failure_count=${NIC_RECOVERY_FAILURE_COUNT}"
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
  run_capture "${diag_dir}/ethtool-${NETWORK_INTERFACE}.log" ethtool "${NETWORK_INTERFACE}"
  run_capture "${diag_dir}/ethtool-driver-${NETWORK_INTERFACE}.log" ethtool -i "${NETWORK_INTERFACE}"
  run_capture "${diag_dir}/journal-kernel-recent.log" journalctl -b -k --since "${KERNEL_NIC_HANG_LOOKBACK}" --no-pager
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
      failures+=("local: service ${service} is not active")
    fi
  done

  if ! mountpoint -q /etc/pve; then
    failures+=("local: /etc/pve is not mounted")
  fi

  if ! timeout 20 pct list >/dev/null 2>&1; then
    failures+=("local: pct list failed or timed out")
  fi

  if ! timeout 20 qm list >/dev/null 2>&1; then
    failures+=("local: qm list failed or timed out")
  fi

  if ! timeout 20 pvesm status >/dev/null 2>&1; then
    failures+=("local: pvesm status failed or timed out")
  fi

  if command -v curl >/dev/null 2>&1; then
    if ! curl -kfsS --max-time 20 https://127.0.0.1:8006/ >/dev/null; then
      failures+=("local: Proxmox web health request failed")
    fi
  fi

  if [[ "${CHECK_GATEWAY}" == "1" ]]; then
    if ! ping -c 2 -W 2 "${GATEWAY}" >/dev/null 2>&1; then
      failures+=("network: gateway ping failed for ${GATEWAY}")
    fi
  fi

  if [[ "${CHECK_OUTBOUND}" == "1" ]] && command -v curl >/dev/null 2>&1; then
    if ! curl -fsS -m 10 --retry 1 -o /dev/null "${OUTBOUND_URL}"; then
      failures+=("network: outbound HTTPS check failed")
    fi
  fi

  if [[ "${CHECK_KERNEL_NIC_HANG}" == "1" ]]; then
    if journalctl -b -k --since "${KERNEL_NIC_HANG_LOOKBACK}" --no-pager --output=cat 2>/dev/null \
      | grep -Eq "e1000e .*${NETWORK_INTERFACE}: Detected Hardware Unit Hang"; then
      failures+=("network: recent e1000e hardware unit hang on ${NETWORK_INTERFACE}")
    fi
  fi

  if ((${#failures[@]} > 0)); then
    printf '%s\n' "${failures[@]}"
    return 1
  fi

  return 0
}

attempt_network_recovery() {
  local reason="$1"
  local diag_dir

  diag_dir="$(collect_diagnostics "pre-network-recovery: ${reason}")"
  echo "Saved pre-recovery diagnostics to ${diag_dir}" >&2

  if [[ "${DRY_RUN}" == "1" ]]; then
    echo "DRY_RUN=1; skipping ${NETWORK_INTERFACE} recovery" >&2
    return 0
  fi

  logger -t homelab-health-watchdog "Attempting ${NETWORK_INTERFACE} link recovery after network health failures; diagnostics: ${diag_dir}"
  ip link set dev "${NETWORK_INTERFACE}" down
  sleep "${NIC_RECOVERY_DOWN_SECONDS}"
  ip link set dev "${NETWORK_INTERFACE}" up
  sleep "${NIC_RECOVERY_SETTLE_SECONDS}"
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

if [[ "${ENABLE_NIC_RECOVERY}" == "1" ]] && ((next_failures == NIC_RECOVERY_FAILURE_COUNT)) && grep -q '^network:' "${failure_output}"; then
  attempt_network_recovery "$(tr '\n' '; ' <"${failure_output}")"

  if check_health >"${failure_output}" 2>&1; then
    echo 0 >"${FAILURE_FILE}"
    echo "Homelab health watchdog checks passed after ${NETWORK_INTERFACE} recovery"
    exit 0
  fi

  echo "Homelab health watchdog checks still failing after ${NETWORK_INTERFACE} recovery:" >&2
  cat "${failure_output}" >&2
fi

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
