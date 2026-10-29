"""Per-source staging area.

Transactions for one source are staged in memory and only committed to the
ledger once the whole source has been read, so a source that fails part-way
leaves no trace in the output.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ledgerflow.models import Rejection, Transaction


@dataclass
class StagingArea:
    source: str
    transactions: list[Transaction] = field(default_factory=list)
    rejections: list[Rejection] = field(default_factory=list)
    duplicates: int = 0
    _ids: set[str] = field(default_factory=set)

    def add(self, txn: Transaction, committed_ids: set[str]) -> bool:
        if txn.txn_id in self._ids or txn.txn_id in committed_ids:
            self.duplicates += 1
            return False
        self._ids.add(txn.txn_id)
        self.transactions.append(txn)
        return True

    def reject(self, record_id: str, reasons: list[str]) -> None:
        self.rejections.append(Rejection(self.source, record_id, list(reasons)))

    def ids(self) -> set[str]:
        return set(self._ids)

    def __len__(self) -> int:
        return len(self.transactions)
