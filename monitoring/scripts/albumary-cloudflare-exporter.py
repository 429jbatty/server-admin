#!/usr/bin/env python3
"""Prometheus exporter for app.albumary.net Cloudflare and RUM metrics."""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


GRAPHQL_URL = "https://api.cloudflare.com/client/v4/graphql"
API_BASE_URL = "https://api.cloudflare.com/client/v4"
DEFAULT_HOSTNAME = "app.albumary.net"
DEFAULT_WINDOW_HOURS = 24
DEFAULT_CACHE_SECONDS = 300


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
        limit: 10
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
      paths: rumPageloadEventsAdaptiveGroups(
        limit: 10
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


class Cache:
    body = ""
    updated_at = 0.0


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    return int(raw)


def metric_escape(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def line(name: str, value: object, labels: dict[str, object] | None = None) -> str:
    if labels:
        label_text = ",".join(f'{key}="{metric_escape(val)}"' for key, val in labels.items())
        return f"{name}{{{label_text}}} {value}"
    return f"{name} {value}"


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
        raise RuntimeError("Set CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_ALBUMARY_ACCOUNT_ID")
    return discovered


def auth_headers() -> dict[str, str]:
    token = os.environ.get("CLOUDFLARE_API_TOKEN")
    api_key = os.environ.get("CLOUDFLARE_API_KEY")
    api_email = os.environ.get("CLOUDFLARE_API_EMAIL")
    if token:
        authorization = token if token.lower().startswith("bearer ") else f"Bearer {token}"
        return {"Authorization": authorization, "Content-Type": "application/json"}
    if api_key and api_email:
        return {
            "X-Auth-Key": api_key,
            "X-Auth-Email": api_email,
            "Content-Type": "application/json",
        }
    raise RuntimeError("Set CLOUDFLARE_API_TOKEN, or CLOUDFLARE_API_KEY plus CLOUDFLARE_API_EMAIL")


def status_buckets(status_rows: list[dict]) -> dict[str, int]:
    buckets = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0}
    for row in status_rows:
        status = str(row.get("dimensions", {}).get("edgeResponseStatus", ""))
        if len(status) == 3 and status[0] in "2345":
            buckets[f"{status[0]}xx"] += int(row.get("count") or 0)
    return buckets


def fetch_metrics() -> dict:
    zone_id = os.environ["CLOUDFLARE_ZONE_ID"]
    account_id = os.environ.get("CLOUDFLARE_ALBUMARY_ACCOUNT_ID") or os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    hostname = os.environ.get("CLOUDFLARE_ALBUMARY_HOSTNAME", DEFAULT_HOSTNAME)
    window_hours = env_int("CLOUDFLARE_ALBUMARY_WINDOW_HOURS", DEFAULT_WINDOW_HOURS)
    end = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    start = end - dt.timedelta(hours=window_hours)
    variables = {
        "zoneTag": zone_id,
        "hostname": hostname,
        "start": start.isoformat().replace("+00:00", "Z"),
        "end": end.isoformat().replace("+00:00", "Z"),
    }
    headers = auth_headers()
    body = cloudflare_json(GRAPHQL_URL, headers, {"query": QUERY, "variables": variables})
    if body.get("errors"):
        raise RuntimeError("; ".join(error.get("message", "Cloudflare GraphQL error") for error in body["errors"]))

    account_id = account_id_for_zone(headers, zone_id, account_id)
    rum_body = cloudflare_json(
        GRAPHQL_URL,
        headers,
        {
            "query": RUM_QUERY,
            "variables": {
                "accountTag": account_id,
                "hostname": hostname,
                "start": variables["start"],
                "end": variables["end"],
            },
        },
    )
    if rum_body.get("errors"):
        raise RuntimeError(
            "; ".join(error.get("message", "Cloudflare RUM GraphQL error") for error in rum_body["errors"])
        )

    zone = ((body.get("data", {}).get("viewer", {}).get("zones") or [{}])[0]) or {}
    totals_row = (zone.get("totals") or [{}])[0] or {}
    totals_sum = totals_row.get("sum") or {}
    account = ((rum_body.get("data", {}).get("viewer", {}).get("accounts") or [{}])[0]) or {}
    rum_totals_row = (account.get("totals") or [{}])[0] or {}
    rum_totals_sum = rum_totals_row.get("sum") or {}
    return {
        "updated_at": end.timestamp(),
        "hostname": hostname,
        "window_hours": window_hours,
        "requests": int(totals_row.get("count") or 0),
        "visits": int(totals_sum.get("visits") or 0),
        "bytes": int(totals_sum.get("edgeResponseBytes") or 0),
        "status": status_buckets(zone.get("status") or []),
        "top_paths": [
            {
                "path": row.get("dimensions", {}).get("clientRequestPath") or "/",
                "requests": int(row.get("count") or 0),
                "bytes": int((row.get("sum") or {}).get("edgeResponseBytes") or 0),
            }
            for row in zone.get("topPaths") or []
        ],
        "page_views": int(rum_totals_row.get("count") or 0),
        "visitors": int(rum_totals_sum.get("visits") or 0),
        "rum_paths": [
            {
                "path": row.get("dimensions", {}).get("requestPath") or "/",
                "page_views": int(row.get("count") or 0),
                "visitors": int((row.get("sum") or {}).get("visits") or 0),
            }
            for row in account.get("paths") or []
        ],
    }


def render_metrics() -> str:
    metrics = fetch_metrics()
    labels = {"hostname": metrics["hostname"], "window": f'{metrics["window_hours"]}h'}
    output = [
        "# HELP albumary_cloudflare_exporter_up Whether the Cloudflare exporter collected successfully.",
        "# TYPE albumary_cloudflare_exporter_up gauge",
        line("albumary_cloudflare_exporter_up", 1, labels),
        "# HELP albumary_cloudflare_last_success_timestamp_seconds Unix timestamp of the last successful Cloudflare collection.",
        "# TYPE albumary_cloudflare_last_success_timestamp_seconds gauge",
        line("albumary_cloudflare_last_success_timestamp_seconds", int(metrics["updated_at"]), labels),
        "# HELP albumary_cloudflare_requests_24h Cloudflare eyeball HTTP requests in the rolling window.",
        "# TYPE albumary_cloudflare_requests_24h gauge",
        line("albumary_cloudflare_requests_24h", metrics["requests"], labels),
        "# HELP albumary_cloudflare_visits_24h Cloudflare HTTP visits in the rolling window.",
        "# TYPE albumary_cloudflare_visits_24h gauge",
        line("albumary_cloudflare_visits_24h", metrics["visits"], labels),
        "# HELP albumary_cloudflare_transfer_bytes_24h Cloudflare edge response bytes in the rolling window.",
        "# TYPE albumary_cloudflare_transfer_bytes_24h gauge",
        line("albumary_cloudflare_transfer_bytes_24h", metrics["bytes"], labels),
        "# HELP albumary_cloudflare_page_views_24h Cloudflare Web Analytics page views in the rolling window.",
        "# TYPE albumary_cloudflare_page_views_24h gauge",
        line("albumary_cloudflare_page_views_24h", metrics["page_views"], labels),
        "# HELP albumary_cloudflare_visitors_24h Cloudflare Web Analytics visitors in the rolling window.",
        "# TYPE albumary_cloudflare_visitors_24h gauge",
        line("albumary_cloudflare_visitors_24h", metrics["visitors"], labels),
        "# HELP albumary_cloudflare_status_responses_24h HTTP response counts by status class in the rolling window.",
        "# TYPE albumary_cloudflare_status_responses_24h gauge",
    ]
    for status_class, count in metrics["status"].items():
        output.append(line("albumary_cloudflare_status_responses_24h", count, {**labels, "status_class": status_class}))

    output.extend(
        [
            "# HELP albumary_cloudflare_top_path_requests_24h Top HTTP paths by request count in the rolling window.",
            "# TYPE albumary_cloudflare_top_path_requests_24h gauge",
            "# HELP albumary_cloudflare_top_path_bytes_24h Top HTTP paths by response bytes in the rolling window.",
            "# TYPE albumary_cloudflare_top_path_bytes_24h gauge",
        ]
    )
    top_paths = metrics["top_paths"] or [{"path": "(none)", "requests": 0, "bytes": 0}]
    for rank, row in enumerate(top_paths, 1):
        output.append(
            line(
                "albumary_cloudflare_top_path_requests_24h",
                row["requests"],
                {**labels, "rank": rank, "path": row["path"]},
            )
        )
        output.append(
            line(
                "albumary_cloudflare_top_path_bytes_24h",
                row["bytes"],
                {**labels, "rank": rank, "path": row["path"]},
            )
        )

    output.extend(
        [
            "# HELP albumary_cloudflare_top_rum_path_page_views_24h Top RUM paths by page view count in the rolling window.",
            "# TYPE albumary_cloudflare_top_rum_path_page_views_24h gauge",
            "# HELP albumary_cloudflare_top_rum_path_visitors_24h Top RUM paths by visitor count in the rolling window.",
            "# TYPE albumary_cloudflare_top_rum_path_visitors_24h gauge",
        ]
    )
    rum_paths = metrics["rum_paths"] or [{"path": "(none)", "page_views": 0, "visitors": 0}]
    for rank, row in enumerate(rum_paths, 1):
        output.append(
            line(
                "albumary_cloudflare_top_rum_path_page_views_24h",
                row["page_views"],
                {**labels, "rank": rank, "path": row["path"]},
            )
        )
        output.append(
            line(
                "albumary_cloudflare_top_rum_path_visitors_24h",
                row["visitors"],
                {**labels, "rank": rank, "path": row["path"]},
            )
        )
    return "\n".join(output) + "\n"


def cached_metrics() -> str:
    now = time.time()
    cache_seconds = env_int("ALBUMARY_CLOUDFLARE_CACHE_SECONDS", DEFAULT_CACHE_SECONDS)
    if Cache.body and now - Cache.updated_at < cache_seconds:
        return Cache.body
    try:
        Cache.body = render_metrics()
        Cache.updated_at = now
        return Cache.body
    except Exception as exc:
        sys.stderr.write(f"Cloudflare collection failed: {exc}\n")
        labels = {"hostname": os.environ.get("CLOUDFLARE_ALBUMARY_HOSTNAME", DEFAULT_HOSTNAME)}
        return "\n".join(
            [
                "# HELP albumary_cloudflare_exporter_up Whether the Cloudflare exporter collected successfully.",
                "# TYPE albumary_cloudflare_exporter_up gauge",
                line("albumary_cloudflare_exporter_up", 0, labels),
                line("albumary_cloudflare_exporter_error_info", 1, {**labels, "message": str(exc)[:180]}),
            ]
        ) + "\n"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok\n")
            return
        if parsed.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return
        body = cached_metrics().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> int:
    host = os.environ.get("ALBUMARY_CLOUDFLARE_EXPORTER_HOST", "0.0.0.0")
    port = env_int("ALBUMARY_CLOUDFLARE_EXPORTER_PORT", 9210)
    server = ThreadingHTTPServer((host, port), Handler)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
