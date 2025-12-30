import os
import time
import requests
from flask import Flask, jsonify

APP = Flask(__name__)

MASTER_JSON = "http://master.openra.net/games?protocol=2&type=json"
NAMES = [n.strip() for n in os.getenv("STATUS_NAMES", "").split(",") if n.strip()]

# Ports: Name -> Port (damit wir sie in der Tabelle zeigen können)
PORTS = {
    "HC-Gaming | OpenRA RA": int(os.getenv("PORT_RA", "1234")),
    "HC-Gaming | OpenRA TD": int(os.getenv("PORT_TD", "1235")),
    "HC-Gaming | OpenRA D2K": int(os.getenv("PORT_D2K", "1236")),
}

# Server-Versionen (hart verdrahtet aus env, falls du willst),
# ansonsten versuchen wir sie aus dem Image-Tag/Repo zu bestimmen (best effort).
# Real: "rmoriz/openra:latest" ist NICHT eindeutig -> daher "unknown" ohne zusätzliche Infos.
SERVER_VERSIONS = {
    "ra": os.getenv("VER_RA", ""),
    "cnc": os.getenv("VER_TD", ""),
    "d2k": os.getenv("VER_D2K", ""),
}

# Cache: mapHash -> {name, ts}
MAP_CACHE = {}
MAP_TTL_SEC = int(os.getenv("MAP_TTL_SEC", "1800"))  # 30min
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "5"))

def fetch_master():
    r = requests.get(MASTER_JSON, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    return r.json()

def normalize_games(data):
    games = data.get("games") if isinstance(data, dict) else data
    if not isinstance(games, list):
        return []
    return games

def map_cache_get(map_hash: str):
    e = MAP_CACHE.get(map_hash)
    if not e:
        return None
    if (time.time() - e["ts"]) > MAP_TTL_SEC:
        MAP_CACHE.pop(map_hash, None)
        return None
    return e["name"]

def map_cache_set(map_hash: str, name: str):
    MAP_CACHE[map_hash] = {"name": name, "ts": time.time()}

def resolve_map_name_best_effort(map_hash: str):
    if not map_hash:
        return None

    cached = map_cache_get(map_hash)
    if cached:
        return cached

    # best-effort: content endpoints (can change)
    candidates = [
        f"https://content.openra.net/maps/{map_hash}",
        f"https://content.openra.net/maps/{map_hash}/meta",
        f"https://content.openra.net/api/maps/{map_hash}",
    ]

    for url in candidates:
        try:
            r = requests.get(url, timeout=HTTP_TIMEOUT, allow_redirects=True)
            if r.status_code != 200:
                continue

            ctype = (r.headers.get("Content-Type") or "").lower()
            if "application/json" in ctype:
                j = r.json()
                name = j.get("name") or j.get("title") or j.get("displayName") or j.get("map")
                if name and isinstance(name, str):
                    map_cache_set(map_hash, name)
                    return name
        except Exception:
            continue

    return None

def build_join_url(game):
    addr = (game.get("address") or "").strip()
    if addr:
        return f"openra://join/{addr}"
    return None

def server_version_for_mod(mod_key: str):
    v = (SERVER_VERSIONS.get(mod_key) or "").strip()
    return v if v else "unknown"

@APP.get("/api/meta")
def meta():
    # Client-Version: du kannst später optional per env setzen, ansonsten unknown
    client_version = (os.getenv("CLIENT_VERSION") or "").strip() or "unknown"

    return jsonify({
        "ts": int(time.time()),
        "clientVersion": client_version,
        "serverVersions": {
            "ra": server_version_for_mod("ra"),
            "cnc": server_version_for_mod("cnc"),
            "d2k": server_version_for_mod("d2k")
        }
    }), 200

@APP.get("/api/status")
def status():
    out = {"ts": int(time.time()), "source": MASTER_JSON, "servers": []}

    try:
        data = fetch_master()
        games = normalize_games(data)
    except Exception as e:
        out["error"] = str(e)
        for wanted in NAMES:
            out["servers"].append({
                "name": wanted,
                "listed": False,
                "listenPort": PORTS.get(wanted),
            })
        return jsonify(out), 200

    for wanted in NAMES:
        match = None
        for g in games:
            name = (g.get("name") or "").strip()
            if name == wanted:
                match = g
                break

        if not match:
            out["servers"].append({
                "name": wanted,
                "listed": False,
                "listenPort": PORTS.get(wanted),
            })
            continue

        map_hash = match.get("map") if isinstance(match.get("map"), str) else None
        map_name = resolve_map_name_best_effort(map_hash) if map_hash else None
        mod_key = match.get("mod")

        out["servers"].append({
            "name": wanted,
            "listed": True,
            "state": match.get("state"),
            "players": match.get("players"),
            "maxPlayers": match.get("maxPlayers"),
            "mapHash": map_hash,
            "mapName": map_name,
            "mod": mod_key,
            "address": match.get("address"),
            "join_url": build_join_url(match),
            "listenPort": PORTS.get(wanted),
            "serverVersion": server_version_for_mod(mod_key) if isinstance(mod_key, str) else "unknown",
        })

    return jsonify(out), 200

if __name__ == "__main__":
    APP.run(host="0.0.0.0", port=8000)
