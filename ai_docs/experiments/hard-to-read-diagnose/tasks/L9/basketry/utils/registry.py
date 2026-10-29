"""A tiny name -> factory registry used for pluggable output renderers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

_RENDERERS: dict[str, Callable[..., Any]] = {}


def register_renderer(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator registering a renderer under ``name`` at import time."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if name in _RENDERERS and _RENDERERS[name] is not func:
            raise ValueError(f"renderer {name!r} already registered")
        _RENDERERS[name] = func
        return func

    return decorator


def get_renderer(name: str) -> Callable[..., Any]:
    try:
        return _RENDERERS[name]
    except KeyError:
        known = ", ".join(sorted(_RENDERERS)) or "none"
        raise KeyError(f"unknown renderer {name!r} (known: {known})") from None


def renderer_names() -> list[str]:
    return sorted(_RENDERERS)
