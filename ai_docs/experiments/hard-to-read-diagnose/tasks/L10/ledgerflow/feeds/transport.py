"""Transports deliver feed pages.

A page is a mapping ``{"items": [...], "next": <token or None>}``. Production
uses the partner gateway; the ``DirectoryTransport`` serves the same page
documents from a directory tree (one directory per feed, one JSON file per
page plus ``index.json``), which is how feed snapshots are replayed locally.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


class FeedError(RuntimeError):
    pass


class FeedNotFound(FeedError):
    pass


class TransientFeedError(FeedError):
    """The gateway timed out or throttled us; the same request may succeed later."""


class Transport:
    def list_feeds(self) -> list[str]:
        raise NotImplementedError

    def describe(self, feed: str) -> dict[str, Any]:
        raise NotImplementedError

    def fetch_page(self, feed: str, token: str | None, since: date | None = None) -> dict[str, Any]:
        raise NotImplementedError


class DirectoryTransport(Transport):
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.requests = 0

    def list_feeds(self) -> list[str]:
        if not self.root.is_dir():
            return []
        return sorted(p.name for p in self.root.iterdir() if (p / "index.json").is_file())

    def describe(self, feed: str) -> dict[str, Any]:
        index = self.root / feed / "index.json"
        if not index.is_file():
            raise FeedNotFound(f"unknown feed {feed!r} under {self.root}")
        with open(index, encoding="utf-8") as fh:
            return json.load(fh)

    def fetch_page(self, feed: str, token: str | None, since: date | None = None) -> dict[str, Any]:
        self.requests += 1
        if token is None:
            token = self.describe(feed)["first"]
        page_path = self.root / feed / f"{token}.json"
        try:
            with open(page_path, encoding="utf-8") as fh:
                page = json.load(fh)
        except FileNotFoundError as exc:
            raise FeedError(f"feed {feed!r}: no page {token!r}") from exc
        except json.JSONDecodeError as exc:
            raise TransientFeedError(f"feed {feed!r}: truncated page {token!r}") from exc
        items = page.get("items", [])
        if since is not None:
            cutoff = since.isoformat()
            items = [it for it in items if str(it.get("posted", "")) >= cutoff]
        log.debug("feed %s page %s: %d items", feed, token, len(items))
        return {"items": items, "next": page.get("next")}
