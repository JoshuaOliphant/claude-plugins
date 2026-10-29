"""Per-channel order defaults.

Each sales channel (web, app, phone, store) has a template that supplies
values a client may leave out of an order request, such as the default
fulfillment method or marketing opt-ins.  Templates live in
``order_defaults.json``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_CHANNEL = "web"


class UnknownChannel(LookupError):
    def __init__(self, channel: str, known: list[str]):
        super().__init__(f"unknown channel {channel!r} (known: {', '.join(known)})")
        self.channel = channel


class OrderTemplates:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._templates: dict[str, dict[str, Any]] | None = None

    def _load(self) -> dict[str, dict[str, Any]]:
        if self._templates is None:
            with self.path.open(encoding="utf-8") as fh:
                templates = json.load(fh)
            if DEFAULT_CHANNEL not in templates:
                raise ValueError(f"{self.path} must define a {DEFAULT_CHANNEL!r} template")
            self._templates = templates
        return self._templates

    def channels(self) -> list[str]:
        return sorted(self._load())

    def for_channel(self, channel: str | None) -> dict[str, Any]:
        templates = self._load()
        name = channel or DEFAULT_CHANNEL
        if name not in templates:
            raise UnknownChannel(name, sorted(templates))
        return templates[name]
