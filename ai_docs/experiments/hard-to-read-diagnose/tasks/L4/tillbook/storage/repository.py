"""Load every configured source once and serve per-office indexes."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Iterable

from tillbook.adapters.codec import DecodeError
from tillbook.adapters.csv_source import RefundCsvSource
from tillbook.adapters.jsonl_source import JsonlTillSource
from tillbook.config import Settings
from tillbook.domain.models import Transaction
from tillbook.domain.offices import OfficeRegistry
from tillbook.storage.index import TimeIndex

log = logging.getLogger(__name__)


@dataclass
class LoadReport:
    loaded: int = 0
    duplicates: list[str] = field(default_factory=list)
    unknown_office: list[str] = field(default_factory=list)
    rejected: list[DecodeError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (self.duplicates or self.unknown_office or self.rejected)


class TransactionRepository:
    def __init__(self, offices: OfficeRegistry) -> None:
        self.offices = offices
        self._indexes: dict[str, TimeIndex] = {code: TimeIndex() for code in offices.codes()}
        self._seen: dict[str, Transaction] = {}
        self.report = LoadReport()

    @classmethod
    def from_settings(cls, settings: Settings, offices: OfficeRegistry | None = None
                      ) -> "TransactionRepository":
        offices = offices or OfficeRegistry.load(settings.path(settings.offices_file))
        repo = cls(offices)
        tills = JsonlTillSource.from_glob(settings.data_dir, settings.transactions_glob,
                                          strict=settings.strict)
        refunds = RefundCsvSource(settings.path(settings.refunds_file), strict=settings.strict)
        repo.ingest(tills)
        repo.ingest(refunds)
        repo.report.rejected.extend(tills.rejected)
        repo.report.rejected.extend(refunds.rejected)
        log.info("loaded %d transactions (%d duplicates, %d rejected)",
                 repo.report.loaded, len(repo.report.duplicates), len(repo.report.rejected))
        return repo

    def ingest(self, transactions: Iterable[Transaction]) -> None:
        for txn in transactions:
            if txn.office not in self.offices:
                self.report.unknown_office.append(txn.txn_id)
                continue
            previous = self._seen.get(txn.txn_id)
            if previous is not None:
                if previous != txn:
                    log.warning("conflicting duplicate %s (%s vs %s)",
                                txn.txn_id, previous.source, txn.source)
                self.report.duplicates.append(txn.txn_id)
                continue
            self._seen[txn.txn_id] = txn
            self._indexes[txn.office].add(txn)
            self.report.loaded += 1

    def index(self, office: str) -> TimeIndex:
        return self._indexes[self.offices.get(office).code]

    def get(self, txn_id: str) -> Transaction | None:
        return self._seen.get(txn_id)

    def all(self) -> list[Transaction]:
        rows: list[Transaction] = []
        for code in sorted(self._indexes):
            rows.extend(self._indexes[code])
        return rows

    def count(self) -> int:
        return len(self._seen)
