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
API_BASE_URL = "https://api.cloudflare.com/client/v4"
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

RUM_QUERY = """
query AlbumaryRumMetrics(
  $accountTag: string!
  $start: Time
  $end: Time
  $hostname: string
) {
  viewer {
    accounts(filter: { accountTag: $accountTag }) {
      totals: rumPageloadEventsAdaptiveGroups(
        limit: 1
        filter: {
          datetime_geq: $start
          datetime_lt: $end
          requestHost: $hostname
        }
      ) {
        count
        sum {
          visits
        }
      }
      hourly: rumPageloadEventsAdaptiveGroups(
        limit: 24
        orderBy: [datetimeHour_DESC]
        filter: {
          datetime_geq: $start
          datetime_lt: $end
          requestHost: $hostname
        }
      ) {
        count
        dimensions {
          datetimeHour
        }
        sum {
          visits
        }
      }
      paths: rumPageloadEventsAdaptiveGroups(
        limit: 8
        orderBy: [count_DESC]
        filter: {
          datetime_geq: $start
          datetime_lt: $end
          requestHost: $hostname
        }
      ) {
        count
        dimensions {
          requestPath
        }
        sum {
          visits
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


def get_config() -> tuple[dict[str, str], str, str | None, str, int]:
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
    account_id = (
        os.environ.get("CLOUDFLARE_ALBUMARY_ACCOUNT_ID")
        or os.environ.get("CLOUDFLARE_ACCOUNT_ID")
        or secrets.get("cloudflare_albumary_account_id")
        or secrets.get("cloudflare_account_id")
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
                account_id,
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
        account_id,
        hostname,
        window_hours,
    )


def cloudflare_json(
    url: str,
    auth_headers: dict[str, str],
    payload: dict | None = None,
    timeout: int = 25,
) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        headers=auth_headers,
        method="POST" if payload is not None else "GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def account_id_for_zone(auth_headers: dict[str, str], zone_id: str, account_id: str | None) -> str:
    if account_id:
        return account_id
    body = cloudflare_json(f"{API_BASE_URL}/zones/{zone_id}", auth_headers)
    if not body.get("success"):
        raise RuntimeError("Cloudflare zone lookup failed while resolving account id")
    discovered = ((body.get("result") or {}).get("account") or {}).get("id")
    if not discovered:
        raise RuntimeError(
            "Set cloudflare_account_id or cloudflare_albumary_account_id in /config/secrets.yaml"
        )
    return discovered


def status_buckets(status_rows: list[dict]) -> dict[str, int]:
    buckets = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0}
    for row in status_rows:
        status = str(row.get("dimensions", {}).get("edgeResponseStatus", ""))
        if len(status) == 3 and status[0] in "2345":
            buckets[f"{status[0]}xx"] += int(row.get("count") or 0)
    return buckets


def request_metrics(
    auth_headers: dict[str, str],
    zone_id: str,
    account_id: str | None,
    hostname: str,
    window_hours: int,
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
    body = cloudflare_json(GRAPHQL_URL, auth_headers, payload)

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
    rum = request_rum_metrics(
        auth_headers,
        account_id_for_zone(auth_headers, zone_id, account_id),
        hostname,
        start,
        end,
    )

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
            "page_views": rum["page_views"],
            "visitors": rum["visitors"],
        },
        "web_analytics": rum,
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


def request_rum_metrics(
    auth_headers: dict[str, str],
    account_id: str,
    hostname: str,
    start: dt.datetime,
    end: dt.datetime,
) -> dict:
    payload = {
        "query": RUM_QUERY,
        "variables": {
            "accountTag": account_id,
            "hostname": hostname,
            "start": start.isoformat().replace("+00:00", "Z"),
            "end": end.isoformat().replace("+00:00", "Z"),
        },
    }
    body = cloudflare_json(GRAPHQL_URL, auth_headers, payload)
    if body.get("errors"):
        raise RuntimeError(
            "; ".join(
                error.get("message", "Cloudflare RUM GraphQL error")
                for error in body["errors"]
            )
        )

    account = ((body.get("data", {}).get("viewer", {}).get("accounts") or [{}])[0]) or {}
    totals_row = (account.get("totals") or [{}])[0] or {}
    totals_sum = totals_row.get("sum") or {}

    return {
        "page_views": int(totals_row.get("count") or 0),
        "visitors": int(totals_sum.get("visits") or 0),
        "hourly": [
            {
                "datetime_hour": row.get("dimensions", {}).get("datetimeHour"),
                "page_views": int(row.get("count") or 0),
                "visitors": int((row.get("sum") or {}).get("visits") or 0),
            }
            for row in account.get("hourly") or []
        ],
        "top_paths": [
            {
                "path": row.get("dimensions", {}).get("requestPath") or "/",
                "page_views": int(row.get("count") or 0),
                "visitors": int((row.get("sum") or {}).get("visits") or 0),
            }
            for row in account.get("paths") or []
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
