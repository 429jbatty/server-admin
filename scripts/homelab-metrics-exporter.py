#!/usr/bin/env python3
"""Small LAN-only JSON metrics exporter for the Homelab dashboard."""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import time as time_module
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from time import time
from typing import Any


GUESTS = [
    {"id": 100, "type": "qemu", "name": "Home Assistant"},
    {"id": 102, "type": "lxc", "name": "AdGuard Home"},
    {"id": 104, "type": "lxc", "name": "Jellyfin"},
    {"id": 106, "type": "lxc", "name": "Media Stack"},
    {"id": 107, "type": "lxc", "name": "Tailscale Subnet Router"},
]
MEDIA_STACK_CT = 106
MEDIA_CONTAINERS = {"bazarr", "jellyseerr", "prowlarr", "qbittorrent", "radarr", "sonarr"}
CPU_SAMPLE_SECONDS = 0.35


def run_json(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return json.loads(result.stdout)


def run_text(command: list[str]) -> str:
    result = subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout


def percent(value: Any, maximum: Any) -> float | None:
    try:
        value_float = float(value)
        maximum_float = float(maximum)
    except (TypeError, ValueError):
        return None

    if maximum_float <= 0:
        return None
    return round((value_float / maximum_float) * 100, 1)


def bytes_to_gib(value: Any) -> float | None:
    try:
        return round(float(value) / 1024 / 1024 / 1024, 1)
    except (TypeError, ValueError):
        return None


def cpu_percent_from_proc_stats(first: str, second: str) -> float | None:
    first = parse_proc_stat(first)
    second = parse_proc_stat(second)
    if not first or not second:
        return None

    idle_delta = second["idle"] - first["idle"]
    total_delta = second["total"] - first["total"]
    if total_delta <= 0:
        return None
    return round((1 - (idle_delta / total_delta)) * 100, 1)


def parse_proc_stat(content: str) -> dict[str, int] | None:
    first_line = content.splitlines()[0] if content else ""
    parts = first_line.split()
    if len(parts) < 5 or parts[0] != "cpu":
        return None

    values = [int(value) for value in parts[1:]]
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    return {"idle": idle, "total": sum(values)}


def read_file(path: str) -> str:
    with open(path, encoding="utf-8") as file:
        return file.read()


def collect_host_cpu_samples() -> dict[str, Any]:
    first = read_file("/proc/stat")
    start = time_module.monotonic()
    time_module.sleep(CPU_SAMPLE_SECONDS)
    second = read_file("/proc/stat")
    elapsed_seconds = time_module.monotonic() - start

    return {"first": first, "second": second, "elapsed_seconds": elapsed_seconds}


def guest_resource_map() -> dict[int, dict[str, Any]]:
    resources = run_json(["pvesh", "get", "/cluster/resources", "--type", "vm", "--output-format", "json"])
    return {int(item["vmid"]): item for item in resources if "vmid" in item}


def node_metrics(node: str, host_cpu_samples: dict[str, Any]) -> dict[str, Any]:
    status = run_json(["pvesh", "get", f"/nodes/{node}/status", "--output-format", "json"])
    rootfs = status.get("rootfs") or {}
    memory = status.get("memory") or {}

    return {
        "name": node,
        "status": "online",
        "cpu_percent": cpu_percent_from_proc_stats(
            host_cpu_samples["first"], host_cpu_samples["second"]
        ),
        "memory_used_gib": bytes_to_gib(memory.get("used")),
        "memory_total_gib": bytes_to_gib(memory.get("total")),
        "memory_percent": percent(memory.get("used"), memory.get("total")),
        "disk_used_gib": bytes_to_gib(rootfs.get("used")),
        "disk_total_gib": bytes_to_gib(rootfs.get("total")),
        "disk_percent": percent(rootfs.get("used"), rootfs.get("total")),
        "uptime_seconds": status.get("uptime"),
    }


def guest_metrics(node: str, guest: dict[str, Any], resource: dict[str, Any]) -> dict[str, Any]:
    guest_type = guest["type"]
    vmid = guest["id"]

    disk_used = resource.get("disk")
    disk_total = resource.get("maxdisk")

    if guest_type == "qemu":
        fsinfo = qemu_data_filesystem(node, vmid)
        if fsinfo:
            disk_used = fsinfo.get("used-bytes")
            disk_total = fsinfo.get("total-bytes")

    return {
        "id": vmid,
        "type": guest_type,
        "name": guest["name"],
        "status": resource.get("status", "unknown"),
        "cpu_percent": round(float(resource.get("cpu", 0)) * 100, 1),
        "memory_used_gib": bytes_to_gib(resource.get("mem")),
        "memory_total_gib": bytes_to_gib(resource.get("maxmem")),
        "memory_percent": percent(resource.get("mem"), resource.get("maxmem")),
        "disk_used_gib": bytes_to_gib(disk_used),
        "disk_total_gib": bytes_to_gib(disk_total),
        "disk_percent": percent(disk_used, disk_total),
        "uptime_seconds": resource.get("uptime"),
    }


def qemu_data_filesystem(node: str, vmid: int) -> dict[str, Any] | None:
    fsinfo = run_json(
        [
            "pvesh",
            "get",
            f"/nodes/{node}/qemu/{vmid}/agent/get-fsinfo",
            "--output-format",
            "json",
        ]
    )
    filesystems = fsinfo.get("result") or []
    for filesystem in filesystems:
        if filesystem.get("mountpoint") == "/mnt/data":
            return filesystem
    return None


def collect() -> dict[str, Any]:
    node = socket.gethostname().split(".")[0]
    host_cpu_samples = collect_host_cpu_samples()
    resources = guest_resource_map()
    payload: dict[str, Any] = {
        "ok": True,
        "updated_at": int(time()),
        "node": {},
        "guests": [],
        "containers": [],
        "errors": [],
    }

    try:
        payload["node"] = node_metrics(node, host_cpu_samples)
    except Exception as exc:  # noqa: BLE001 - exporter should report partial failures.
        payload["ok"] = False
        payload["errors"].append({"scope": "node", "message": str(exc)})

    for guest in GUESTS:
        try:
            payload["guests"].append(guest_metrics(node, guest, resources.get(guest["id"], {})))
        except Exception as exc:  # noqa: BLE001
            payload["ok"] = False
            payload["errors"].append(
                {"scope": f"{guest['type']}:{guest['id']}", "message": str(exc)}
            )

    try:
        payload["containers"] = media_container_metrics()
    except Exception as exc:  # noqa: BLE001
        payload["ok"] = False
        payload["errors"].append({"scope": "media-containers", "message": str(exc)})

    return payload


def media_container_metrics() -> list[dict[str, Any]]:
    output = run_text(
        [
            "pct",
            "exec",
            str(MEDIA_STACK_CT),
            "--",
            "bash",
            "-lc",
            "docker stats --no-stream --format json",
        ]
    )
    containers = []
    for line in output.splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        name = item.get("Name")
        if name not in MEDIA_CONTAINERS:
            continue
        containers.append(
            {
                "name": name,
                "cpu_percent": parse_percent(item.get("CPUPerc")),
                "memory_percent": parse_percent(item.get("MemPerc")),
                "memory_usage": item.get("MemUsage"),
                "net_io": item.get("NetIO"),
                "block_io": item.get("BlockIO"),
                "pids": int(item.get("PIDs", 0)),
            }
        )
    return sorted(containers, key=lambda container: container["name"])


def parse_percent(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(str(value).strip().rstrip("%")), 2)
    except ValueError:
        return None


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - stdlib API
        if self.path not in {"/", "/metrics/homelab"}:
            self.send_error(404)
            return

        body = json.dumps(collect(), sort_keys=True).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=9108, type=int)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
