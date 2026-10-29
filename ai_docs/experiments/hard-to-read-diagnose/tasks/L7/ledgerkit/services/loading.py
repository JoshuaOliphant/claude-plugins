"""Reading ledgers from disk."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from ledgerkit.config import Config, load_config
from ledgerkit.importers import ImportReport, importer_registry, load_importers
from ledgerkit.models import Ledger
from ledgerkit.utils.dates import parse_period


@dataclass
class LoadResult:
    ledger: Ledger
    report: ImportReport
    importer: str


def resolve_importer(path: Path, input_format: str | None = None):
    load_importers()
    if input_format:
        return importer_registry.get(input_format)
    return importer_registry.for_extension(path.suffix)


def load_ledger(
    path: str | os.PathLike,
    *,
    input_format: str | None = None,
    config: Config | None = None,
    strict: bool = True,
    period: str | None = None,
    account: str | None = None,
) -> LoadResult:
    config = config or load_config()
    path = Path(path)
    importer_cls = resolve_importer(path, input_format)
    importer = importer_cls(currency=config.get("ledger", "currency", "USD"), strict=strict)
    text = path.read_text(encoding="utf-8")
    ledger, report = importer.load(text, source=path.name)
    if period:
        start, end = parse_period(period)
        ledger = ledger.between(start, end)
    if account:
        ledger = ledger.filter(lambda t: t.account == account)
    return LoadResult(ledger, report, importer_cls.name)
