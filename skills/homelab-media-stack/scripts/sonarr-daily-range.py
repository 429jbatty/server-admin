#!/usr/bin/env python3
"""Inspect or repair a Sonarr daily-show air-date range without exposing keys."""

import argparse
import datetime as dt
import json
import os
import sqlite3
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


def api_key(path):
    return ET.parse(path).getroot().findtext("ApiKey")


def request(base, key, method, path, payload=None, params=None, timeout=300):
    url = base.rstrip("/") + path
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"X-Api-Key": key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read()
        return json.loads(raw) if raw else None


def online_backup(database):
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = f"{database}.daily-range.{stamp}.bak"
    source_db = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    destination_db = sqlite3.connect(destination)
    source_db.backup(destination_db)
    destination_db.close()
    source_db.close()
    stat = os.stat(database)
    os.chown(destination, stat.st_uid, stat.st_gid)
    return destination


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tvdb-id", type=int, required=True)
    parser.add_argument("--start", type=dt.date.fromisoformat, required=True)
    parser.add_argument("--end", type=dt.date.fromisoformat, required=True)
    parser.add_argument("--expected-count", type=int, required=True)
    parser.add_argument("--apply", action="store_true", help="set Daily and monitor the range")
    parser.add_argument("--verify-date", type=dt.date.fromisoformat)
    parser.add_argument("--search", action="store_true", help="automatically search and grab the range")
    parser.add_argument("--base-url", default="http://127.0.0.1:8989")
    parser.add_argument("--config", default="/data/config/sonarr/config.xml")
    parser.add_argument("--database", default="/data/config/sonarr/sonarr.db")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.start > args.end:
        raise SystemExit("Start date must not be after end date")
    if args.verify_date and not args.start <= args.verify_date <= args.end:
        raise SystemExit("Verification date must be inside the target range")
    if args.search and not args.verify_date:
        raise SystemExit("Refusing search: --verify-date is required with --search")

    key = api_key(args.config)
    series = next(
        (s for s in request(args.base_url, key, "GET", "/api/v3/series") if s.get("tvdbId") == args.tvdb_id),
        None,
    )
    if not series:
        raise SystemExit(f"No Sonarr series found for TVDB ID {args.tvdb_id}")
    episodes = request(
        args.base_url,
        key,
        "GET",
        "/api/v3/episode",
        params={"seriesId": series["id"]},
    )
    target = sorted(
        [
            episode for episode in episodes
            if episode.get("airDate")
            and args.start <= dt.date.fromisoformat(episode["airDate"]) <= args.end
        ],
        key=lambda episode: episode["airDate"],
    )
    if len(target) != args.expected_count:
        raise SystemExit(
            f"Safety check failed: expected {args.expected_count} episodes, found {len(target)}"
        )
    if not target or target[0]["airDate"] != args.start.isoformat() or target[-1]["airDate"] != args.end.isoformat():
        raise SystemExit("Safety check failed: episode boundary dates do not match")

    summary = {
        "series": {"id": series["id"], "title": series["title"], "seriesType": series.get("seriesType")},
        "range": {
            "start": args.start.isoformat(),
            "end": args.end.isoformat(),
            "count": len(target),
            "monitored": sum(bool(e.get("monitored")) for e in target),
            "withFiles": sum(bool(e.get("hasFile")) for e in target),
        },
        "outsideMonitored": sum(bool(e.get("monitored")) for e in episodes if e not in target),
        "backup": None,
        "verification": None,
        "searchCommand": None,
    }

    if args.apply:
        summary["backup"] = online_backup(args.database)
        series["seriesType"] = "daily"
        series["monitored"] = True
        updated = request(args.base_url, key, "PUT", f"/api/v3/series/{series['id']}", series)
        request(
            args.base_url,
            key,
            "PUT",
            "/api/v3/episode/monitor",
            {"episodeIds": [e["id"] for e in target], "monitored": True},
        )
        summary["series"]["seriesType"] = updated.get("seriesType")
        summary["range"]["monitored"] = len(target)

    if args.verify_date:
        episode = next(e for e in target if e["airDate"] == args.verify_date.isoformat())
        releases = request(
            args.base_url,
            key,
            "GET",
            "/api/v3/release",
            params={"episodeId": episode["id"]},
        )
        summary["verification"] = {
            "airDate": episode["airDate"],
            "releaseCount": len(releases),
            "approvedCount": sum(bool(r.get("approved")) for r in releases),
            "results": [
                {
                    "title": release.get("title"),
                    "indexer": release.get("indexer"),
                    "seeders": release.get("seeders"),
                    "approved": release.get("approved"),
                    "rejections": release.get("rejections"),
                }
                for release in releases[:5]
            ],
        }
        if args.search and summary["verification"]["approvedCount"] == 0:
            raise SystemExit("Refusing search: verification returned no approved releases")

    if args.search:
        if series.get("seriesType") != "daily" and not args.apply:
            raise SystemExit("Refusing search: series is not Daily; run with --apply first")
        active_commands = request(args.base_url, key, "GET", "/api/v3/command")
        active_searches = [
            command for command in active_commands
            if command.get("name") == "EpisodeSearch"
            and command.get("status") in ("queued", "started")
        ]
        if active_searches:
            raise SystemExit(
                "Refusing search: another EpisodeSearch command is already queued or started"
            )
        current = request(
            args.base_url,
            key,
            "GET",
            "/api/v3/episode",
            params={"seriesId": series["id"]},
        )
        current_by_id = {episode["id"]: episode for episode in current}
        unmonitored = [episode for episode in target if not current_by_id[episode["id"]].get("monitored")]
        if unmonitored:
            raise SystemExit(
                f"Refusing search: {len(unmonitored)} target episodes are not monitored"
            )
        missing = [
            episode for episode in target
            if current_by_id[episode["id"]].get("monitored")
            and not current_by_id[episode["id"]].get("hasFile")
        ]
        if not missing:
            summary["searchCommand"] = {"status": "not-needed", "episodeCount": 0}
        else:
            command = request(
                args.base_url,
                key,
                "POST",
                "/api/v3/command",
                {"name": "EpisodeSearch", "episodeIds": [e["id"] for e in missing]},
            )
            summary["searchCommand"] = {
                "id": command.get("id"),
                "status": command.get("status"),
                "episodeCount": len(missing),
            }

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
