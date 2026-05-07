#!/usr/bin/env python3
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


def api_key(path):
    return ET.parse(path).findtext("ApiKey")


def request(method, url, api_key_value=None, body=None, headers=None):
    data = None
    req_headers = headers.copy() if headers else {}
    if body is not None:
        data = json.dumps(body).encode()
        req_headers["Content-Type"] = "application/json"
    if api_key_value:
        req_headers["X-Api-Key"] = api_key_value
    req = urllib.request.Request(url, data=data, method=method, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors="replace")
        raise RuntimeError(f"{method} {url} failed: HTTP {exc.code}: {raw}") from exc


def ensure_root_folder(base_url, key, path):
    roots = request("GET", f"{base_url}/api/v3/rootfolder", key)
    if any(root.get("path") == path for root in roots):
        return "exists"
    request("POST", f"{base_url}/api/v3/rootfolder", key, {"path": path})
    return "created"


def get_qbit_password():
    logs = subprocess.check_output(["docker", "logs", "qbittorrent"], text=True, stderr=subprocess.STDOUT)
    match = re.search(r"temporary password is provided for this session:\s*(\S+)", logs, re.IGNORECASE)
    if not match:
        match = re.search(r"password is:\s*(\S+)", logs, re.IGNORECASE)
    if not match:
        raise RuntimeError("Could not find qBittorrent temporary password in container logs")
    return match.group(1)


def qbit_login(password):
    data = urllib.parse.urlencode({"username": "admin", "password": password}).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:8080/api/v2/auth/login",
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        cookie = resp.headers.get("Set-Cookie")
        body = resp.read().decode()
    if body != "Ok." or not cookie:
        raise RuntimeError("qBittorrent login failed")
    return cookie


def qbit_post(path, cookie, values, ignore_conflict=False):
    data = urllib.parse.urlencode(values).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:8080/api/v2/{path}",
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded", "Cookie": cookie},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            resp.read()
    except urllib.error.HTTPError as exc:
        if ignore_conflict and exc.code in (400, 409):
            return
        raise


def ensure_qbit(password):
    cookie = qbit_login(password)
    qbit_post(
        "app/setPreferences",
        cookie,
        {
            "json": json.dumps(
                {
                    "save_path": "/data/downloads/complete",
                    "temp_path_enabled": True,
                    "temp_path": "/data/downloads/incomplete",
                    "create_subfolder_enabled": True,
                }
            )
        },
    )
    qbit_post(
        "torrents/createCategory",
        cookie,
        {"category": "radarr", "savePath": "/data/downloads/complete/radarr"},
        ignore_conflict=True,
    )
    qbit_post(
        "torrents/createCategory",
        cookie,
        {"category": "sonarr", "savePath": "/data/downloads/complete/sonarr"},
        ignore_conflict=True,
    )


def qbit_fields(category, password):
    return [
        {"name": "host", "value": "qbittorrent"},
        {"name": "port", "value": 8080},
        {"name": "useSsl", "value": False},
        {"name": "urlBase", "value": ""},
        {"name": "username", "value": "admin"},
        {"name": "password", "value": password},
        {"name": category["field"], "value": category["value"]},
        {"name": category["imported_field"], "value": ""},
        {"name": category["recent_field"], "value": 0},
        {"name": category["older_field"], "value": 0},
        {"name": "initialState", "value": 0},
        {"name": "sequentialOrder", "value": False},
        {"name": "firstAndLast", "value": False},
        {"name": "contentLayout", "value": 0},
    ]


def ensure_download_client(base_url, key, name, fields):
    clients = request("GET", f"{base_url}/api/v3/downloadclient", key)
    if any(client.get("name") == name for client in clients):
        return "exists"
    payload = {
        "enable": True,
        "protocol": "torrent",
        "priority": 1,
        "removeCompletedDownloads": True,
        "removeFailedDownloads": True,
        "name": name,
        "fields": fields,
        "implementationName": "qBittorrent",
        "implementation": "QBittorrent",
        "configContract": "QBittorrentSettings",
        "tags": [],
    }
    request("POST", f"{base_url}/api/v3/downloadclient", key, payload)
    return "created"


def ensure_prowlarr_app(prowlarr_key, name, implementation, target_url, target_key, categories):
    apps = request("GET", "http://127.0.0.1:9696/api/v1/applications", prowlarr_key)
    if any(app.get("name") == name for app in apps):
        return "exists"
    payload = {
        "name": name,
        "syncLevel": "fullSync",
        "enable": True,
        "implementationName": implementation,
        "implementation": implementation,
        "configContract": f"{implementation}Settings",
        "fields": [
            {"name": "prowlarrUrl", "value": "http://prowlarr:9696"},
            {"name": "baseUrl", "value": target_url},
            {"name": "apiKey", "value": target_key},
            {"name": "syncCategories", "value": categories},
            {"name": "syncRejectBlocklistedTorrentHashesWhileGrabbing", "value": False},
        ],
        "tags": [],
    }
    if implementation == "Sonarr":
        payload["fields"].insert(4, {"name": "animeSyncCategories", "value": [5070]})
        payload["fields"].insert(5, {"name": "syncAnimeStandardFormatSearch", "value": True})
    request("POST", "http://127.0.0.1:9696/api/v1/applications", prowlarr_key, payload)
    return "created"


def main():
    radarr_key = api_key("/data/config/radarr/config.xml")
    sonarr_key = api_key("/data/config/sonarr/config.xml")
    prowlarr_key = api_key("/data/config/prowlarr/config.xml")
    qbit_password = get_qbit_password()

    results = []
    results.append(("radarr_root", ensure_root_folder("http://127.0.0.1:7878", radarr_key, "/data/library/movies")))
    results.append(("sonarr_root", ensure_root_folder("http://127.0.0.1:8989", sonarr_key, "/data/library/tv")))
    ensure_qbit(qbit_password)
    results.append(
        (
            "radarr_qbit",
            ensure_download_client(
                "http://127.0.0.1:7878",
                radarr_key,
                "qBittorrent",
                qbit_fields(
                    {
                        "field": "movieCategory",
                        "value": "radarr",
                        "imported_field": "movieImportedCategory",
                        "recent_field": "recentMoviePriority",
                        "older_field": "olderMoviePriority",
                    },
                    qbit_password,
                ),
            ),
        )
    )
    results.append(
        (
            "sonarr_qbit",
            ensure_download_client(
                "http://127.0.0.1:8989",
                sonarr_key,
                "qBittorrent",
                qbit_fields(
                    {
                        "field": "tvCategory",
                        "value": "sonarr",
                        "imported_field": "tvImportedCategory",
                        "recent_field": "recentTvPriority",
                        "older_field": "olderTvPriority",
                    },
                    qbit_password,
                ),
            ),
        )
    )
    results.append(
        (
            "prowlarr_radarr",
            ensure_prowlarr_app(
                prowlarr_key,
                "Radarr",
                "Radarr",
                "http://radarr:7878",
                radarr_key,
                [2000, 2010, 2020, 2030, 2040, 2045, 2050, 2060, 2070, 2080, 2090],
            ),
        )
    )
    results.append(
        (
            "prowlarr_sonarr",
            ensure_prowlarr_app(
                prowlarr_key,
                "Sonarr",
                "Sonarr",
                "http://sonarr:8989",
                sonarr_key,
                [5000, 5010, 5020, 5030, 5040, 5045, 5050, 5090],
            ),
        )
    )
    for name, status in results:
        print(f"{name}: {status}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
