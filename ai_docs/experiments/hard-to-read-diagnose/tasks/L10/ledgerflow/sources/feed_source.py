"""Partner feeds read through the feed client."""

from __future__ import annotations

from datetime import date
from typing import Any, Iterator

from ledgerflow.feeds.client import FeedClient
from ledgerflow.sources.base import RawRecord, Source


class FeedSource(Source):
    kind = "feed"

    def __init__(self, name: str, client: FeedClient, feed: str, *, since: date | None = None):
        super().__init__(name)
        self.client = client
        self.feed = feed
        self.since = since
        self.pages_seen = 0

    def records(self) -> Iterator[RawRecord]:
        cursor = self.client.open_cursor(self.feed, since=self.since)
        for page in cursor:
            self.pages_seen += 1
            for item in page:
                yield self._to_record(item)

    def _to_record(self, item: dict[str, Any]) -> RawRecord:
        return RawRecord(
            record_id=str(item.get("id", "")),
            posted=str(item.get("posted", "")),
            amount=str(item.get("amount", "")),
            currency=str(item.get("currency", "")).upper(),
            account=str(item.get("account", "")),
            memo=str(item.get("memo", "")),
            extra={k: v for k, v in item.items()
                   if k not in {"id", "posted", "amount", "currency", "account", "memo"}},
        )

    def describe(self) -> str:
        meta = self.client.describe(self.feed)
        return f"feed:{self.feed} ({meta.get('title', 'untitled')})"
