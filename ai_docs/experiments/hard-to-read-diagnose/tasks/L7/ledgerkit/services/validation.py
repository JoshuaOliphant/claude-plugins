"""Consistency checks over a loaded ledger."""

from __future__ import annotations

import datetime as _dt
from collections import Counter
from dataclasses import dataclass, field

from ledgerkit.config import Config
from ledgerkit.models import Ledger


@dataclass
class Issue:
    level: str
    txn_id: str
    message: str

    def __str__(self) -> str:
        return f"[{self.level}] {self.txn_id}: {self.message}"


@dataclass
class ValidationResult:
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors


CHECKS = []


def check(fn):
    CHECKS.append(fn)
    return fn


@check
def duplicate_ids(ledger: Ledger, config: Config, today: _dt.date):
    counts = Counter(t.txn_id for t in ledger)
    for txn_id, n in sorted(counts.items()):
        if n > 1:
            yield Issue("error", txn_id, f"appears {n} times")


@check
def future_dates(ledger: Ledger, config: Config, today: _dt.date):
    allowed = _dt.timedelta(days=config.get_int("validation", "max_future_days", 0))
    for txn in ledger:
        if txn.date > today + allowed:
            yield Issue("warning", txn.txn_id, f"dated in the future ({txn.date.isoformat()})")


@check
def zero_amounts(ledger: Ledger, config: Config, today: _dt.date):
    if config.get_bool("validation", "allow_zero"):
        return
    for txn in ledger:
        if not txn.amount:
            yield Issue("warning", txn.txn_id, "amount is zero")


@check
def known_categories(ledger: Ledger, config: Config, today: _dt.date):
    allowed = set(config.get_list("validation", "categories"))
    if not allowed:
        return
    for txn in ledger:
        if txn.category not in allowed and txn.top_category not in allowed:
            yield Issue("warning", txn.txn_id, f"unknown category {txn.category!r}")


@check
def missing_payee(ledger: Ledger, config: Config, today: _dt.date):
    for txn in ledger:
        if not txn.payee:
            yield Issue("error", txn.txn_id, "payee is empty")


def validate(ledger: Ledger, config: Config, today: _dt.date) -> ValidationResult:
    result = ValidationResult()
    for fn in CHECKS:
        result.issues.extend(fn(ledger, config, today))
    return result
