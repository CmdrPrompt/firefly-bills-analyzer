"""UC7 cache layer: generic, TTL-aware JSON file cache (FR-21, FR-22, NFR-09)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


def _path(name: str, cache_dir: Path) -> Path:
    return cache_dir / f"{name}.json"


def read(name: str, ttl_seconds: int, cache_dir: Path) -> Any | None:
    """Return the cached value for ``name``, or ``None`` if missing/stale/unreadable.

    A cache entry is stale when more than ``ttl_seconds`` have passed since it
    was written.
    """
    path = _path(name, cache_dir)
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError, KeyError):
        return None

    if time.time() - payload["timestamp"] > ttl_seconds:
        return None
    return payload["data"]


def write(name: str, data: Any, cache_dir: Path) -> None:
    """Write ``data`` for ``name`` to ``<cache_dir>/<name>.json`` with a timestamp.

    Creates ``cache_dir`` if it does not already exist.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp": time.time(), "data": data}
    _path(name, cache_dir).write_text(json.dumps(payload))


def invalidate(name: str, cache_dir: Path) -> None:
    """Delete the cache file for ``name``, if it exists."""
    _path(name, cache_dir).unlink(missing_ok=True)


def clear_all(cache_dir: Path) -> None:
    """Delete every cache file in ``cache_dir``."""
    if not cache_dir.exists():
        return
    for path in cache_dir.glob("*.json"):
        path.unlink(missing_ok=True)
