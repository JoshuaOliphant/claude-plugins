"""Domain objects shared across the import pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from ledgerflow.money import Money


@dataclass(frozen=True, slots=True)
class Transaction:
    """A normalised ledger entry.

    ``amount`` is in the currency the counterparty used; ``amount_base`` is the
    same value converted into the ledger's base currency on the posting date.
    """

    txn_id: str
    posted: date
    amount: Money
    amount_base: Money
    account: str
    memo: str
    category: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.txn_id,
            "posted": self.posted.isoformat(),
            "amount": str(self.amount.amount),
            "currency": self.amount.currency,
            "amount_base": str(self.amount_base.amount),
            "base_currency": self.amount_base.currency,
            "account": self.account,
            "memo": self.memo,
            "category": self.category,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Transaction":
        return cls(
            txn_id=data["id"],
            posted=date.fromisoformat(data["posted"]),
            amount=Money(Decimal(data["amount"]), data["currency"]),
            amount_base=Money(Decimal(data["amount_base"]), data["base_currency"]),
            account=data["account"],
            memo=data["memo"],
            category=data["category"],
            source=data["source"],
        )


@dataclass(slots=True)
class Rejection:
    source: str
    record_id: str
    reasons: list[str]

    def describe(self) -> str:
        return f"{self.source}:{self.record_id}: {'; '.join(self.reasons)}"


@dataclass(slots=True)
class SourceResult:
    name: str
    imported: int = 0
    rejected: int = 0
    duplicates: int = 0
    attempts: int = 1
    rejections: list[Rejection] = field(default_factory=list)

    def line(self) -> str:
        extra = f" after {self.attempts} attempts" if self.attempts > 1 else ""
        return (f"{self.name}: {self.imported} imported, {self.rejected} rejected, "
                f"{self.duplicates} duplicates{extra}")


@dataclass(slots=True)
class ImportResult:
    output: str
    base_currency: str
    sources: list[SourceResult] = field(default_factory=list)

    @property
    def imported(self) -> int:
        return sum(s.imported for s in self.sources)

    @property
    def rejected(self) -> int:
        return sum(s.rejected for s in self.sources)

    def by_name(self, name: str) -> SourceResult:
        for result in self.sources:
            if result.name == name:
                return result
        raise KeyError(name)
