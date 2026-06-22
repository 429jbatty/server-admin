#!/usr/bin/env python3
"""Validate homelab Grafana dashboard JSON without third-party packages."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GLOB = ROOT / "monitoring/grafana/dashboards"
BUILTIN_VARIABLES = {
    "__dashboard",
    "__from",
    "__interval",
    "__interval_ms",
    "__name",
    "__org",
    "__rate_interval",
    "__to",
    "__user",
}
VARIABLE_RE = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)[^}]*\}|([A-Za-z_][A-Za-z0-9_]*))")
UID_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
SECRET_KEYS = {"authorization", "api_key", "apikey", "password", "secret", "token"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path, help="dashboard JSON files")
    return parser.parse_args()


def rectangles_overlap(a: dict[str, int], b: dict[str, int]) -> bool:
    return not (
        a["x"] + a["w"] <= b["x"]
        or b["x"] + b["w"] <= a["x"]
        or a["y"] + a["h"] <= b["y"]
        or b["y"] + b["h"] <= a["y"]
    )


def find_secret_keys(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key.lower() in SECRET_KEYS and child not in (None, "", [], {}):
                findings.append(child_path)
            findings.extend(find_secret_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(find_secret_keys(child, f"{path}[{index}]"))
    return findings


def validate(path: Path) -> tuple[dict[str, Any] | None, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        dashboard = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"cannot parse JSON: {exc}"], warnings

    if not isinstance(dashboard, dict):
        return None, ["top-level JSON must be an object"], warnings

    title = dashboard.get("title")
    uid = dashboard.get("uid")
    panels = dashboard.get("panels")
    if not isinstance(title, str) or not title.strip():
        errors.append("missing non-empty title")
    if not isinstance(uid, str) or not UID_RE.fullmatch(uid):
        errors.append("uid must contain 1-40 letters, digits, underscores, or hyphens")
    if not isinstance(panels, list) or not panels:
        errors.append("panels must be a non-empty list")
        panels = []

    panel_ids: set[int] = set()
    rectangles: list[tuple[int, dict[str, int]]] = []
    for index, panel in enumerate(panels):
        prefix = f"panel[{index}]"
        if not isinstance(panel, dict):
            errors.append(f"{prefix} must be an object")
            continue
        panel_id = panel.get("id")
        if not isinstance(panel_id, int):
            errors.append(f"{prefix} has no integer id")
            continue
        if panel_id in panel_ids:
            errors.append(f"duplicate panel id {panel_id}")
        panel_ids.add(panel_id)
        if not isinstance(panel.get("title"), str) or not panel["title"].strip():
            errors.append(f"panel {panel_id} has no title")
        grid = panel.get("gridPos")
        if not isinstance(grid, dict) or any(not isinstance(grid.get(k), int) for k in ("x", "y", "w", "h")):
            errors.append(f"panel {panel_id} has invalid gridPos")
            continue
        if grid["x"] < 0 or grid["y"] < 0 or grid["w"] <= 0 or grid["h"] <= 0:
            errors.append(f"panel {panel_id} has non-positive or negative grid coordinates")
        if grid["x"] + grid["w"] > 24:
            errors.append(f"panel {panel_id} extends past the 24-column grid")
        if panel.get("type") != "row":
            rectangles.append((panel_id, grid))
        for target_index, target in enumerate(panel.get("targets", [])):
            if isinstance(target, dict) and "expr" in target and not str(target["expr"]).strip():
                errors.append(f"panel {panel_id} target[{target_index}] has an empty PromQL expression")

    for offset, (left_id, left) in enumerate(rectangles):
        for right_id, right in rectangles[offset + 1 :]:
            if rectangles_overlap(left, right):
                errors.append(f"panels {left_id} and {right_id} overlap")

    templating = dashboard.get("templating", {}).get("list", [])
    defined = {item.get("name") for item in templating if isinstance(item, dict) and isinstance(item.get("name"), str)}
    serialized = json.dumps({"panels": panels, "links": dashboard.get("links", [])})
    referenced = {match.group(1) or match.group(2) for match in VARIABLE_RE.finditer(serialized)}
    unknown = sorted(referenced - defined - BUILTIN_VARIABLES)
    unused = sorted(defined - referenced)
    if unknown:
        errors.append(f"undefined dashboard variables: {', '.join(unknown)}")
    if unused:
        warnings.append(f"unused dashboard variables: {', '.join(unused)}")

    secret_paths = find_secret_keys(dashboard)
    if secret_paths:
        errors.append("possible embedded secret fields: " + ", ".join(secret_paths))
    return dashboard, errors, warnings


def main() -> int:
    args = parse_args()
    files = args.files or sorted(DEFAULT_GLOB.glob("*.json"))
    if not files:
        print("ERROR: no dashboard JSON files found", file=sys.stderr)
        return 2

    dashboards: list[tuple[Path, dict[str, Any]]] = []
    failed = False
    for path in files:
        dashboard, errors, warnings = validate(path)
        label = str(path)
        for warning in warnings:
            print(f"WARN  {label}: {warning}")
        for error in errors:
            print(f"ERROR {label}: {error}", file=sys.stderr)
        if errors:
            failed = True
        if dashboard is not None:
            dashboards.append((path, dashboard))
            print(f"OK    {label}: {dashboard.get('title', '?')} ({len(dashboard.get('panels', []))} panels)")

    uid_paths: dict[str, Path] = {}
    for path, dashboard in dashboards:
        uid = dashboard.get("uid")
        if isinstance(uid, str) and uid in uid_paths:
            print(f"ERROR duplicate dashboard uid {uid}: {uid_paths[uid]} and {path}", file=sys.stderr)
            failed = True
        elif isinstance(uid, str):
            uid_paths[uid] = path

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
