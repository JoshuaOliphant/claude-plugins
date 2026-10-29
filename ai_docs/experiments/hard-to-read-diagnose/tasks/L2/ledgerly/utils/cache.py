"""Tiny file-keyed memoisation for loaders.

Reference data files (customers, FX tables) are read many times per command;
this caches the parsed result keyed on path and modification time, so an
edited file is picked up without restarting.
"""

from __future__ import annotations

import functools
import os
from pathlib import Path

_REGISTRY: list = []


def file_memo(func):
    cache: dict[tuple[str, int], object] = {}

    @functools.wraps(func)
    def wrapper(path, *args, **kwargs):
        resolved = str(Path(path).resolve())
        try:
            mtime = os.stat(resolved).st_mtime_ns
        except FileNotFoundError:
            return func(path, *args, **kwargs)
        key = (resolved, mtime)
        if args or kwargs:
            return func(path, *args, **kwargs)
        if key not in cache:
            for old in [k for k in cache if k[0] == resolved]:
                del cache[old]
            cache[key] = func(path)
        return cache[key]

    wrapper.cache_clear = cache.clear
    _REGISTRY.append(wrapper)
    return wrapper


def clear_all() -> None:
    for wrapper in _REGISTRY:
        wrapper.cache_clear()
