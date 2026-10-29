"""Application wiring: build everything a run needs from a config."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Callable, Iterator

from ledgerflow.categorize import load_categorizer
from ledgerflow.config import Config, load_config
from ledgerflow.feeds.client import FeedClient
from ledgerflow.feeds.transport import DirectoryTransport, Transport
from ledgerflow.fx import load_rates
from ledgerflow.models import ImportResult, Transaction
from ledgerflow.normalize import Normalizer
from ledgerflow.pipeline import RETRYABLE, ImportPipeline
from ledgerflow.sources import build_source
from ledgerflow.storage import LedgerStore, read_ledger
from ledgerflow.utils.retry import RetryPolicy, retrying
from ledgerflow.validation import Validator

log = logging.getLogger(__name__)


def _as_config(config: Config | str | Path) -> Config:
    return config if isinstance(config, Config) else load_config(config)


def run_import(
    config: Config | str | Path,
    *,
    validate: bool | None = None,
    transport: Transport | None = None,
    only: list[str] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> ImportResult:
    """Import every configured source into the ledger file named by the config.

    ``validate`` overrides ``[validation] enabled``; ``transport`` replaces the
    directory transport built from ``[feeds] root`` (used to point at a live
    gateway or a recorded session); ``only`` restricts the run to named sources.
    """
    cfg = _as_config(config)
    if validate is not None:
        cfg = cfg.with_validation(validate)

    rates = load_rates(cfg.fx_rates)
    normalizer = Normalizer(rates, load_categorizer(cfg.categories), cfg.base_currency)
    validator = None
    if cfg.validation.enabled:
        validator = Validator(rates, sample_size=cfg.validation.sample_size,
                              reject_zero_amounts=cfg.validation.reject_zero_amounts)

    client = FeedClient(transport or DirectoryTransport(cfg.feeds_root))
    selected = [s for s in cfg.sources if not only or s.name in only]
    if only:
        unknown = set(only) - {s.name for s in selected}
        if unknown:
            raise KeyError(f"unknown source(s): {', '.join(sorted(unknown))}")
    sources = [build_source(s, feed_client=client) for s in selected]

    pipeline = ImportPipeline(
        normalizer=normalizer,
        store=LedgerStore(cfg.output),
        policy=RetryPolicy.from_config(cfg.retry, RETRYABLE),
        validator=validator,
        sleep=sleep,
    )
    try:
        return pipeline.run(sources)
    finally:
        client.close()
        for source in sources:
            source.close()


def load_ledger(path: str | Path) -> Iterator[Transaction]:
    return read_ledger(path)


def list_feeds(config: Config | str | Path, transport: Transport | None = None) -> list[dict]:
    cfg = _as_config(config)
    client = FeedClient(transport or DirectoryTransport(cfg.feeds_root))
    describe = retrying(RetryPolicy.from_config(cfg.retry, RETRYABLE))(client.describe)
    return [describe(name) for name in client.feeds()]


def check_sources(config: Config | str | Path, transport: Transport | None = None) -> list[str]:
    """Run only the preflight checks and return one line per source."""
    cfg = _as_config(config)
    rates = load_rates(cfg.fx_rates)
    validator = Validator(rates, sample_size=cfg.validation.sample_size,
                          reject_zero_amounts=cfg.validation.reject_zero_amounts)
    client = FeedClient(transport or DirectoryTransport(cfg.feeds_root))
    lines = []
    try:
        for s in cfg.sources:
            report = validator.preflight(build_source(s, feed_client=client))
            problems = ", ".join(f"{k} x{n}" for k, n in report.problems.items()) or "no problems"
            lines.append(f"{s.name}: sampled {report.sampled}, {problems}")
    finally:
        client.close()
    return lines
