"""Helpers for working with nested mapping data (JSON payloads, settings files)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import Any

_MISSING = object()


def deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    """Return a new dict with ``override`` layered on top of ``base``.

    Nested mappings present on both sides are merged recursively; any other
    value from ``override`` replaces the one in ``base``.  Neither input is
    modified.
    """
    result = dict(base)
    for key, value in override.items():
        current = result.get(key)
        if isinstance(value, Mapping) and isinstance(current, Mapping):
            result[key] = deep_merge(current, value)
        else:
            result[key] = value
    return result


def get_path(data: Mapping[str, Any], path: str, default: Any = None) -> Any:
    """Look up a dotted path such as ``"shipping.rates.standard"``."""
    node: Any = data
    for part in path.split("."):
        if not isinstance(node, Mapping):
            return default
        node = node.get(part, _MISSING)
        if node is _MISSING:
            return default
    return node


def require_path(data: Mapping[str, Any], path: str) -> Any:
    """Like :func:`get_path` but raise ``KeyError`` when the path is absent."""
    value = get_path(data, path, _MISSING)
    if value is _MISSING:
        raise KeyError(path)
    return value


def pick(data: Mapping[str, Any], keys: Iterable[str]) -> dict[str, Any]:
    """Return a dict containing only ``keys`` that exist in ``data``."""
    return {key: data[key] for key in keys if key in data}


def without(data: Mapping[str, Any], keys: Iterable[str]) -> dict[str, Any]:
    """Return a shallow copy of ``data`` minus ``keys``."""
    drop = set(keys)
    return {key: value for key, value in data.items() if key not in drop}


def flatten(data: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    """Flatten nested mappings into dotted keys (lists are left as leaves)."""
    flat: dict[str, Any] = {}
    for key, value in data.items():
        dotted = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, Mapping) and value:
            flat.update(flatten(value, dotted))
        else:
            flat[dotted] = value
    return flat


def freeze(data: Any) -> Any:
    """Recursively convert dicts to read-only proxies and lists to tuples."""
    if isinstance(data, Mapping):
        return MappingProxyType({key: freeze(value) for key, value in data.items()})
    if isinstance(data, list):
        return tuple(freeze(item) for item in data)
    return data


def thaw(data: Any) -> Any:
    """Inverse of :func:`freeze`: produce plain, independent dicts and lists."""
    if isinstance(data, Mapping):
        return {key: thaw(value) for key, value in data.items()}
    if isinstance(data, (list, tuple)):
        return [thaw(item) for item in data]
    return data
