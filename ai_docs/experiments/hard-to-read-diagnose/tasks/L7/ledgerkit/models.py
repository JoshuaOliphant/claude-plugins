"""Domain model: transactions and the ledger that holds them."""

from __future__ import annotations

import datetime as _dt
import hashlib
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Callable, Iterable, Iterator

from ledgerkit.money import DEFAULT_CURRENCY, Money, total
from ledgerkit.utils.dates import month_key


@dataclass(frozen=True)
class Transaction:
    date: _dt.date
    payee: str
    account: str
    amount: Money
    category: str = "uncategorized"
    memo: str = ""
    tags: tuple[str, ...] = ()
    txn_id: str = ""

    def __post_init__(self) -> None:
        if not self.txn_id:
            object.__setattr__(self, "txn_id", self.fingerprint())

    def fingerprint(self) -> str:
        basis = "|".join(
            [self.date.isoformat(), self.payee, self.account, self.amount.plain(), self.amount.currency]
        )
        return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:12]

    @property
    def is_expense(self) -> bool:
        return self.amount.is_negative

    @property
    def top_category(self) -> str:
        return self.category.split(":", 1)[0]


@dataclass
class Ledger:
    transactions: list[Transaction] = field(default_factory=list)
    currency: str = DEFAULT_CURRENCY
    source: str = ""

    def __iter__(self) -> Iterator[Transaction]:
        return iter(self.transactions)

    def __len__(self) -> int:
        return len(self.transactions)

    def add(self, txn: Transaction) -> None:
        if txn.amount.currency != self.currency:
            raise ValueError(
                f"transaction {txn.txn_id} is in {txn.amount.currency}, ledger is {self.currency}"
            )
        self.transactions.append(txn)

    def extend(self, txns: Iterable[Transaction]) -> None:
        for txn in txns:
            self.add(txn)

    def sorted(self) -> "Ledger":
        ordered = sorted(self.transactions, key=lambda t: (t.date, t.account, t.payee, t.txn_id))
        return Ledger(ordered, self.currency, self.source)

    def filter(self, predicate: Callable[[Transaction], bool]) -> "Ledger":
        return Ledger([t for t in self.transactions if predicate(t)], self.currency, self.source)

    def between(self, start: _dt.date | None, end: _dt.date | None) -> "Ledger":
        def keep(t: Transaction) -> bool:
            if start and t.date < start:
                return False
            if end and t.date > end:
                return False
            return True

        return self.filter(keep)

    def accounts(self) -> list[str]:
        return sorted({t.account for t in self.transactions})

    def categories(self) -> list[str]:
        return sorted({t.category for t in self.transactions})

    def balance(self, account: str | None = None) -> Money:
        return total(
            (t.amount for t in self.transactions if account is None or t.account == account),
            self.currency,
        )

    def running_balances(self) -> list[tuple[Transaction, Money]]:
        running = Money.zero(self.currency)
        out = []
        for txn in self.sorted():
            running = running + txn.amount
            out.append((txn, running))
        return out

    def totals_by(self, key: Callable[[Transaction], str]) -> "OrderedDict[str, Money]":
        buckets: dict[str, Money] = {}
        for txn in self.transactions:
            k = key(txn)
            buckets[k] = buckets.get(k, Money.zero(self.currency)) + txn.amount
        return OrderedDict(sorted(buckets.items()))

    def totals_by_category(self) -> "OrderedDict[str, Money]":
        return self.totals_by(lambda t: t.category)

    def totals_by_month(self) -> "OrderedDict[str, Money]":
        return self.totals_by(lambda t: month_key(t.date))

    def date_range(self) -> tuple[_dt.date, _dt.date] | None:
        if not self.transactions:
            return None
        dates = [t.date for t in self.transactions]
        return min(dates), max(dates)
