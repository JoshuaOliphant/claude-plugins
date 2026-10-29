"""A small persistent result cache.

Results are stored as one JSON document per entry under
``<cache_dir>/<namespace>/<kk>/<key>.json`` where ``key`` is the SHA-256 of
the canonical call signature.  Entries survive across processes, which keeps
large manifest re-runs and repeated desk quotes cheap.

Only JSON-serialisable return values can be memoised.  Writes are atomic
(temp file + ``os.replace``) so concurrent desk processes never observe a
half-written entry; unreadable entries are treated as misses and rewritten.
"""

from __future__ import annotations

import functools
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

from freightdesk.utils.log import get_logger

log = get_logger(__name__)

ENTRY_FORMAT = 1


def canonical(value: Any) -> Any:
    """Convert call arguments into a stable, JSON-friendly representation."""
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [canonical(v) for v in value]
    if isinstance(value, dict):
        return {str(k): canonical(v) for k, v in sorted(value.items())}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"cannot build a cache key from {type(value).__name__}")


def make_key(fn_name: str, args: tuple, kwargs: dict) -> tuple[str, dict]:
    material = {"fn": fn_name, "args": canonical(args), "kwargs": canonical(kwargs)}
    blob = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest(), material


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    writes: int = 0
    errors: int = 0


@dataclass
class DiskCache:
    root: Path
    namespace: str
    stats: CacheStats = field(default_factory=CacheStats)

    @property
    def directory(self) -> Path:
        return self.root / self.namespace

    def path_for(self, key: str) -> Path:
        return self.directory / key[:2] / f"{key}.json"

    def get(self, key: str) -> tuple[bool, Any]:
        path = self.path_for(key)
        try:
            with path.open("r", encoding="utf-8") as fh:
                entry = json.load(fh)
        except FileNotFoundError:
            self.stats.misses += 1
            return False, None
        except (OSError, ValueError) as exc:
            log.warning("discarding unreadable cache entry %s: %s", path, exc)
            self.stats.errors += 1
            self.stats.misses += 1
            return False, None
        if entry.get("format") != ENTRY_FORMAT or "value" not in entry:
            self.stats.misses += 1
            return False, None
        self.stats.hits += 1
        return True, entry["value"]

    def put(self, key: str, value: Any, material: dict | None = None) -> None:
        path = self.path_for(key)
        entry = {
            "format": ENTRY_FORMAT,
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "call": material,
            "value": value,
        }
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(entry, fh, indent=1, sort_keys=True)
                fh.write("\n")
            os.replace(tmp, path)
            self.stats.writes += 1
        except OSError as exc:
            # A read-only or full cache must never break rating.
            log.warning("could not write cache entry %s: %s", path, exc)
            self.stats.errors += 1

    def entries(self) -> list[Path]:
        if not self.directory.is_dir():
            return []
        return sorted(self.directory.glob("*/*.json"))


_caches: dict[str, DiskCache] = {}


def cache_for(namespace: str) -> DiskCache:
    """Return the process-wide cache for ``namespace``."""
    from freightdesk.config import load_settings

    root = load_settings().cache_dir
    cache = _caches.get(namespace)
    if cache is None or cache.root != root:
        cache = DiskCache(root=root, namespace=namespace)
        _caches[namespace] = cache
    return cache


def all_caches() -> dict[str, DiskCache]:
    return dict(_caches)


def memoize_to_disk(namespace: str) -> Callable[[Callable], Callable]:
    """Memoise a function's JSON result in the persistent cache.

    The key is derived from the function's qualified name and its
    canonicalised arguments, so the decorated function must be
    deterministic in its arguments.
    """

    def decorator(fn: Callable) -> Callable:
        fn_name = f"{fn.__module__}.{fn.__qualname__}"

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            cache = cache_for(namespace)
            key, material = make_key(fn_name, args, kwargs)
            found, value = cache.get(key)
            if found:
                return value
            value = fn(*args, **kwargs)
            cache.put(key, value, material)
            return value

        wrapper.cache_namespace = namespace
        return wrapper

    return decorator
