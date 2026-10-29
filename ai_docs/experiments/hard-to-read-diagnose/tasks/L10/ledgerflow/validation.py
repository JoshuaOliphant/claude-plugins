"""Optional strict validation.

``preflight`` samples the head of a source before anything is staged, so a
source with a wrong column mapping or an unknown currency fails before it can
write half a ledger. ``check`` applies the stricter per-record rules.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from itertools import islice

from ledgerflow.fx import RateTable
from ledgerflow.money import MoneyError, parse_amount
from ledgerflow.sources.base import RawRecord, Source
from ledgerflow.utils.dates import DateError, parse_date

log = logging.getLogger(__name__)


class ValidationError(ValueError):
    pass


@dataclass
class PreflightReport:
    source: str
    sampled: int = 0
    problems: Counter = field(default_factory=Counter)
    currencies: Counter = field(default_factory=Counter)

    @property
    def problem_rate(self) -> float:
        return sum(self.problems.values()) / self.sampled if self.sampled else 0.0


class Validator:
    def __init__(self, rates: RateTable, *, sample_size: int = 25,
                 reject_zero_amounts: bool = True, max_problem_rate: float = 0.5):
        self.rates = rates
        self.sample_size = sample_size
        self.reject_zero_amounts = reject_zero_amounts
        self.max_problem_rate = max_problem_rate

    def preflight(self, source: Source) -> PreflightReport:
        report = PreflightReport(source.name)
        for record in islice(source.records(), self.sample_size):
            report.sampled += 1
            report.currencies[record.currency] += 1
            for problem in self.check(record):
                report.problems[problem.split(":", 1)[0]] += 1
        if report.sampled == 0:
            raise ValidationError(f"{source.name}: source produced no records")
        if report.problem_rate > self.max_problem_rate:
            worst = ", ".join(f"{k} x{n}" for k, n in report.problems.most_common(3))
            raise ValidationError(f"{source.name}: {report.problem_rate:.0%} of sampled records "
                                  f"are invalid ({worst})")
        log.info("%s: preflight sampled %d records, currencies %s",
                 source.name, report.sampled, dict(report.currencies))
        return report

    def check(self, record: RawRecord) -> list[str]:
        problems = [f"missing: {name}" for name in record.missing()]
        if problems:
            return problems
        try:
            parse_date(record.posted, record.date_format)
        except DateError as exc:
            problems.append(f"date: {exc}")
        try:
            value = parse_amount(record.amount)
            if self.reject_zero_amounts and value == 0:
                problems.append("amount: zero-value transaction")
        except MoneyError as exc:
            problems.append(f"amount: {exc}")
        if not self.rates.knows(record.currency):
            problems.append(f"currency: no rates for {record.currency}")
        if not record.memo.strip():
            problems.append("memo: empty description")
        return problems
