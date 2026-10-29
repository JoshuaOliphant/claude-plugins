"""Feed client: pagination on top of a transport."""

from __future__ import annotations

import logging
from collections import OrderedDict
from datetime import date
from typing import Any, Iterator

from ledgerflow.feeds.transport import Transport

log = logging.getLogger(__name__)


class PageCursor(Iterator[list[dict[str, Any]]]):
    """Walks a feed page by page, following ``next`` tokens."""

    def __init__(self, transport: Transport, feed: str, since: date | None = None):
        self._transport = transport
        self.feed = feed
        self.since = since
        self._token: str | None = None
        self._started = False
        self.closed = False
        self.pages_read = 0

    def __iter__(self) -> "PageCursor":
        return self

    def __next__(self) -> list[dict[str, Any]]:
        if self.closed or (self._started and self._token is None):
            self.closed = True
            raise StopIteration
        page = self._transport.fetch_page(self.feed, self._token, since=self.since)
        self._started = True
        self._token = page.get("next")
        self.pages_read += 1
        return list(page.get("items", []))

    def close(self) -> None:
        self.closed = True

    def __repr__(self) -> str:
        return f"<PageCursor {self.feed} since={self.since} pages={self.pages_read}>"


class FeedClient:
    """Entry point for reading partner feeds.

    The partner gateway caps concurrent cursors per API key, so the client keeps
    the cursors it has opened and hands back the open one for the same feed
    window rather than starting another.
    """

    def __init__(self, transport: Transport, *, max_open_cursors: int = 4):
        self.transport = transport
        self.max_open_cursors = max_open_cursors
        self._open: OrderedDict[tuple[str, date | None], PageCursor] = OrderedDict()

    def feeds(self) -> list[str]:
        return self.transport.list_feeds()

    def describe(self, feed: str) -> dict[str, Any]:
        return self.transport.describe(feed)

    def open_cursor(self, feed: str, since: date | None = None) -> PageCursor:
        key = (feed, since)
        cursor = self._open.get(key)
        if cursor is None or cursor.closed:
            self._evict()
            cursor = PageCursor(self.transport, feed, since)
            self._open[key] = cursor
            log.debug("opened %r", cursor)
        else:
            self._open.move_to_end(key)
        return cursor

    def _evict(self) -> None:
        for key in [k for k, c in self._open.items() if c.closed]:
            del self._open[key]
        while len(self._open) >= self.max_open_cursors:
            _, oldest = self._open.popitem(last=False)
            oldest.close()

    def iter_items(self, feed: str, since: date | None = None) -> Iterator[dict[str, Any]]:
        for page in self.open_cursor(feed, since):
            yield from page

    def close(self) -> None:
        for cursor in self._open.values():
            cursor.close()
        self._open.clear()
