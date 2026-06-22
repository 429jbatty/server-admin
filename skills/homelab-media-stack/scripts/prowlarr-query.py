#!/usr/bin/env python3
"""Run sanitized, read-only searches against the live Prowlarr API."""

import argparse
import collections
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


def api_key(path):
    return ET.parse(path).getroot().findtext("ApiKey")


def get(base, path, key, params=None, timeout=240):
    url = base.rstrip("/") + path
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    request = urllib.request.Request(url, headers={"X-Api-Key": key})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", action="append", required=True)
    parser.add_argument("--title-contains")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--base-url", default="http://127.0.0.1:9696")
    parser.add_argument("--config", default="/data/config/prowlarr/config.xml")
    args = parser.parse_args()

    key = api_key(args.config)
    indexers = get(args.base_url, "/api/v1/indexer", key)
    health = get(args.base_url, "/api/v1/health", key)
    output = {
        "indexers": [
            {"name": item.get("name"), "enabled": item.get("enable")}
            for item in indexers
        ],
        "health": [
            {
                "type": item.get("type"),
                "source": item.get("source"),
                "message": item.get("message"),
            }
            for item in health
        ],
        "searches": [],
    }

    needle = args.title_contains.lower() if args.title_contains else None
    for query in args.query:
        results = get(
            args.base_url,
            "/api/v1/search",
            key,
            {"query": query, "type": "search", "limit": args.limit, "offset": 0},
        )
        if needle:
            results = [r for r in results if needle in r.get("title", "").lower()]
        output["searches"].append({
            "query": query,
            "count": len(results),
            "byIndexer": dict(collections.Counter(r.get("indexer") for r in results)),
            "results": [
                {
                    "title": result.get("title"),
                    "indexer": result.get("indexer"),
                    "publishDate": result.get("publishDate"),
                    "seeders": result.get("seeders"),
                    "size": result.get("size"),
                    "categories": [c.get("name") for c in result.get("categories", [])],
                }
                for result in results[: args.top]
            ],
        })
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
