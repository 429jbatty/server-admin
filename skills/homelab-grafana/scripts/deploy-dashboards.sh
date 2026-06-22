#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 [--retire RUNTIME.json] DASHBOARD.json [...]" >&2
}

PVE_HOST="${PVE_HOST:-pve-nuc}"
CTID="${GRAFANA_CTID:-108}"
RUNTIME_DIR="/opt/monitoring/grafana/dashboards"
RETIRE=()
FILES=()

while (($#)); do
  case "$1" in
    --retire)
      [[ $# -ge 2 ]] || { usage; exit 2; }
      RETIRE+=("$2")
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --*)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
    *)
      FILES+=("$1")
      shift
      ;;
  esac
done

((${#FILES[@]})) || { usage; exit 2; }

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CHECKER="$SCRIPT_DIR/check-dashboards.py"
python3 "$CHECKER" "${FILES[@]}"

for retired in "${RETIRE[@]}"; do
  [[ "$retired" =~ ^[A-Za-z0-9._-]+\.json$ ]] || {
    echo "Unsafe runtime filename: $retired" >&2
    exit 2
  }
done

declare -a UIDS=()
for file in "${FILES[@]}"; do
  [[ -f "$file" ]] || { echo "Missing file: $file" >&2; exit 2; }
  uid="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["uid"])' "$file")"
  [[ "$uid" =~ ^[A-Za-z0-9_-]{1,40}$ ]] || { echo "Unsafe UID: $uid" >&2; exit 2; }
  UIDS+=("$uid")
done

ssh "$PVE_HOST" "pct status $CTID" | grep -q 'status: running'
ssh "$PVE_HOST" "pct exec $CTID -- test -d '$RUNTIME_DIR'"

stamp="$(date +%Y%m%d-%H%M%S)"
for retired in "${RETIRE[@]}"; do
  ssh "$PVE_HOST" "pct exec $CTID -- bash -lc 'set -eu; file=\"$RUNTIME_DIR/$retired\"; if test -f \"\$file\"; then mv \"\$file\" \"\$file.pre-deploy-$stamp\"; fi'"
done

for file in "${FILES[@]}"; do
  base="$(basename -- "$file")"
  [[ "$base" =~ ^[A-Za-z0-9._-]+\.json$ ]] || { echo "Unsafe filename: $base" >&2; exit 2; }
  remote_tmp="/tmp/homelab-grafana-$stamp-$base"
  scp -q "$file" "$PVE_HOST:$remote_tmp"
  ssh "$PVE_HOST" "set -eu; if pct exec $CTID -- test -f '$RUNTIME_DIR/$base'; then pct exec $CTID -- cp '$RUNTIME_DIR/$base' '$RUNTIME_DIR/$base.pre-deploy-$stamp'; fi; pct push $CTID '$remote_tmp' '$RUNTIME_DIR/$base'; rm -f '$remote_tmp'"
done

ssh "$PVE_HOST" "pct exec $CTID -- bash -lc 'cd /opt/monitoring && docker compose restart grafana'"
sleep 3
ssh "$PVE_HOST" "pct exec $CTID -- bash -lc 'cd /opt/monitoring && ! docker compose logs --since=2m grafana | grep -Eiq \"provision.*(error|fail)|error.*provision\"'"
ssh "$PVE_HOST" "pct exec $CTID -- curl -fsS http://127.0.0.1:3000/api/health >/dev/null"

for uid in "${UIDS[@]}"; do
  verify="set -a; . /opt/monitoring/secrets/grafana.env; set +a; curl -fsS -u \"\${GF_SECURITY_ADMIN_USER:-admin}:\${GF_SECURITY_ADMIN_PASSWORD}\" \"http://127.0.0.1:3000/api/dashboards/uid/$uid\" >/dev/null"
  ssh "$PVE_HOST" "pct exec $CTID -- bash -lc '$verify'"
  echo "Verified dashboard UID: $uid"
done

echo "Grafana dashboard deployment complete."
