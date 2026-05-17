#!/usr/bin/env python3
"""Idempotently create the MVP Uptime Kuma monitors."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

from uptime_kuma_api import MonitorType, UptimeKumaApi


@dataclass(frozen=True)
class Monitor:
    name: str
    url: str
    ignore_tls: bool = False
    accepted_statuscodes: tuple[str, ...] = ("200-299",)


MONITORS = [
    Monitor("Home Assistant", "http://192.168.1.187:8123"),
    Monitor("Jellyfin", "http://192.168.1.191:8096"),
    Monitor("AdGuard Home", "http://192.168.1.189"),
    Monitor("Albumary Public Website", "https://app.albumary.net"),
    Monitor("Grafana", "http://127.0.0.1:3000"),
    Monitor("Prometheus", "http://127.0.0.1:9090/-/ready"),
    Monitor("Proxmox UI", "https://192.168.1.184:8006", ignore_tls=True),
]


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def main() -> int:
    url = os.environ.get("UPTIME_KUMA_URL", "http://127.0.0.1:3001")
    username = required_env("UPTIME_KUMA_USERNAME")
    password = required_env("UPTIME_KUMA_PASSWORD")

    with UptimeKumaApi(url, timeout=20) as api:
        if api.need_setup():
            api.setup(username, password)
        api.login(username, password)

        existing = {monitor["name"] for monitor in api.get_monitors()}
        for monitor in MONITORS:
            if monitor.name in existing:
                print(f"exists: {monitor.name}")
                continue
            api.add_monitor(
                type=MonitorType.HTTP,
                name=monitor.name,
                url=monitor.url,
                interval=60,
                retryInterval=60,
                maxretries=2,
                timeout=20,
                ignoreTls=monitor.ignore_tls,
                accepted_statuscodes=list(monitor.accepted_statuscodes),
            )
            print(f"created: {monitor.name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
