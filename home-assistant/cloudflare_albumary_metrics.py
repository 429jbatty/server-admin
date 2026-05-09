#!/usr/bin/env python3
"""Fetch Cloudflare GraphQL metrics for app.albumary.net for Home Assistant."""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request


GRAPHQL_URL = "https://api.cloudflare.com/client/v4/graphql"
DEFAULT_HOSTNAME = "app.albumary.net"
DEFAULT_WINDOW_HOURS = 24
SECRETS_PATH = "/config/secrets.yaml"


QUERY = """
query AlbumaryMetrics(
  $zoneTag: string
  $start: Time
  $end: Time
  $hostname: string
) {
  viewer {
    zones(filter: { zoneTag: $zoneTag }) {
      totals: httpRequestsAdaptiveGroups(
        limit: 1
        filter: {
          datetime_geq: $start
          datetime_lt: $end
          requestSource: "eyeball"
          clientRequestHTTPHost: $hostname
        }
      ) {
        count
        sum {
          edgeResponseBytes
          visits
        }
      }
      hourly: httpRequestsAdaptiveGroups(
        limit: 24
        orderBy: [datetimeHour_DESC]
        filter: {
          datetime_geq: $start
          datetime_lt: $end
          requestSource: "eyeball"
          clientRequestHTTPHost: $hostname
        }
      ) {
        count
        dimensions {
          datetimeHour
        }
        sum {
          edgeResponseBytes
          visits
        }
      }
      status: httpRequestsAdaptiveGroups(
        limit: 20
        orderBy: [count_DESC]
        filter: {
          datetime_geq: $start
          datetime_lt: $end
          requestSource: "eyeball"
          clientRequestHTTPHost: $hostname
        }
      ) {
        count
        dimensions {
          edgeResponseStatus
        }
      }
      topPaths: httpRequestsAdaptiveGroups(
        limit: 8
        orderBy: [count_DESC]
        filter: {
          datetime_geq: $start
          datetime_lt: $end
          requestSource: "eyeball"
          clientRequestHTTPHost: $hostname
        }
      ) {
        count
        dimensions {
          clientRequestPath
        }
        sum {
          edgeResponseBytes
        }
      }
    }
  }
}
"""


def read_simple_secrets(path: str = SECRETS_PATH) -> dict[str, str]:
    secrets: dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.split("#", 1)[0].strip()
                if not line or ":" not in line:
                    continue
                key, value = line.split(":", 1)
                value = value.strip().strip("'\"")
                if key.strip() and value:
                    secrets[key.strip()] = value
    except FileNotFoundError:
        pass
    return secrets


def get_config() -> tuple[dict[str, str], str, str, int]:
    secrets = read_simple_secrets()
    token = os.environ.get("CLOUDFLARE_API_TOKEN") or secrets.get("cloudflare_api_token")
    api_key = os.environ.get("CLOUDFLARE_API_KEY") or secrets.get("cloudflare_api_key")
    api_email = os.environ.get("CLOUDFLARE_API_EMAIL") or secrets.get("cloudflare_api_email")
    zone_id = (
        os.environ.get("CLOUDFLARE_ALBUMARY_ZONE_ID")
        or os.environ.get("CLOUDFLARE_ZONE_ID")
        or secrets.get("cloudflare_albumary_zone_id")
        or secrets.get("cloudflare_zone_id")
    )
    hostname = (
        os.environ.get("CLOUDFLARE_ALBUMARY_HOSTNAME")
        or secrets.get("cloudflare_albumary_hostname")
        or DEFAULT_HOSTNAME
    )
    window_hours = int(
        os.environ.get("CLOUDFLARE_ALBUMARY_WINDOW_HOURS")
        or secrets.get("cloudflare_albumary_window_hours")
        or DEFAULT_WINDOW_HOURS
    )
    if not token or not zone_id:
        if api_key and api_email and zone_id:
            return (
                {
                    "X-Auth-Key": api_key,
                    "X-Auth-Email": api_email,
                    "Content-Type": "application/json",
                },
                zone_id,
                hostname,
                window_hours,
            )
        raise RuntimeError(
            "Set cloudflare_api_token and cloudflare_zone_id, or cloudflare_api_key plus cloudflare_api_email and cloudflare_zone_id, in /config/secrets.yaml"
        )
    authorization = token if token.lower().startswith("bearer ") else f"Bearer {token}"
    return (
        {
            "Authorization": authorization,
            "Content-Type": "application/json",
        },
        zone_id,
        hostname,
        window_hours,
    )


def status_buckets(status_rows: list[dict]) -> dict[str, int]:
    buckets = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0}
    for row in status_rows:
        status = str(row.get("dimensions", {}).get("edgeResponseStatus", ""))
        if len(status) == 3 and status[0] in "2345":
            buckets[f"{status[0]}xx"] += int(row.get("count") or 0)
    return buckets


def request_metrics(
    auth_headers: dict[str, str], zone_id: str, hostname: str, window_hours: int
) -> dict:
    end = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    start = end - dt.timedelta(hours=window_hours)
    payload = {
        "query": QUERY,
        "variables": {
            "zoneTag": zone_id,
            "hostname": hostname,
            "start": start.isoformat().replace("+00:00", "Z"),
            "end": end.isoformat().replace("+00:00", "Z"),
        },
    }
    request = urllib.request.Request(
        GRAPHQL_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=auth_headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        body = json.loads(response.read().decode("utf-8"))

    if body.get("errors"):
        raise RuntimeError(
            "; ".join(
                error.get("message", "Cloudflare GraphQL error") for error in body["errors"]
            )
        )

    zone = ((body.get("data", {}).get("viewer", {}).get("zones") or [{}])[0]) or {}
    totals_row = (zone.get("totals") or [{}])[0] or {}
    totals_sum = totals_row.get("sum") or {}
    buckets = status_buckets(zone.get("status") or [])

    return {
        "ok": True,
        "updated_at": end.isoformat().replace("+00:00", "Z"),
        "hostname": hostname,
        "window_hours": window_hours,
        "totals": {
            "requests": int(totals_row.get("count") or 0),
            "visits": int(totals_sum.get("visits") or 0),
            "bytes": int(totals_sum.get("edgeResponseBytes") or 0),
            "status_2xx": buckets["2xx"],
            "status_3xx": buckets["3xx"],
            "status_4xx": buckets["4xx"],
            "status_5xx": buckets["5xx"],
        },
        "hourly": [
            {
                "datetime_hour": row.get("dimensions", {}).get("datetimeHour"),
                "requests": int(row.get("count") or 0),
                "visits": int((row.get("sum") or {}).get("visits") or 0),
                "bytes": int((row.get("sum") or {}).get("edgeResponseBytes") or 0),
            }
            for row in zone.get("hourly") or []
        ],
        "top_paths": [
            {
                "path": row.get("dimensions", {}).get("clientRequestPath") or "/",
                "requests": int(row.get("count") or 0),
                "bytes": int((row.get("sum") or {}).get("edgeResponseBytes") or 0),
            }
            for row in zone.get("topPaths") or []
        ],
    }


def main() -> int:
    try:
        print(json.dumps(request_metrics(*get_config()), separators=(",", ":")))
        return 0
    except (RuntimeError, urllib.error.URLError, TimeoutError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "updated_at": dt.datetime.now(dt.timezone.utc)
                    .replace(microsecond=0)
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "error": str(exc),
                },
                separators=(",", ":"),
            )
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
