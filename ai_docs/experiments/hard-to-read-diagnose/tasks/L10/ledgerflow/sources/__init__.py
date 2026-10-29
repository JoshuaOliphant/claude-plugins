"""Source construction from configuration."""

from __future__ import annotations

from ledgerflow.config import SourceConfig
from ledgerflow.feeds.client import FeedClient
from ledgerflow.sources.base import RawRecord, Source
from ledgerflow.sources.csv_source import CsvSource
from ledgerflow.sources.feed_source import FeedSource
from ledgerflow.sources.jsonl_source import JsonlSource

__all__ = ["RawRecord", "Source", "CsvSource", "JsonlSource", "FeedSource", "build_source"]


def build_source(cfg: SourceConfig, *, feed_client: FeedClient | None = None) -> Source:
    if cfg.kind == "csv":
        return CsvSource(
            cfg.name,
            cfg.path,
            date_format=cfg.date_format,
            delimiter=cfg.options.get("delimiter"),
            encoding=cfg.options.get("encoding", "utf-8-sig"),
            default_currency=cfg.options.get("currency"),
        )
    if cfg.kind == "jsonl":
        return JsonlSource(cfg.name, cfg.path, encoding=cfg.options.get("encoding", "utf-8"))
    if cfg.kind == "feed":
        if feed_client is None:
            raise ValueError(f"source {cfg.name!r} needs a feed client")
        return FeedSource(cfg.name, feed_client, cfg.feed, since=cfg.since)
    raise ValueError(f"unknown source kind {cfg.kind!r}")
