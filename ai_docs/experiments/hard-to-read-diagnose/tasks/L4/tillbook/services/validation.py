"""Data quality checks run before reports are published."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date

from tillbook.domain.models import Kind, Transaction
from tillbook.storage.repository import TransactionRepository


@dataclass
class Finding:
    severity: str
    code: str
    message: str
    txn_id: str | None = None

    def to_json(self) -> dict:
        return {"severity": self.severity, "code": self.code, "message": self.message,
                "txn": self.txn_id}


@dataclass
class ValidationResult:
    findings: list[Finding] = field(default_factory=list)
    per_day: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "error"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "warning"]

    def to_json(self) -> dict:
        return {
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "findings": [f.to_json() for f in self.findings],
            "per_day": self.per_day,
        }


class Validator:
    def __init__(self, repository: TransactionRepository) -> None:
        self.repository = repository
        self.offices = repository.offices

    def run(self) -> ValidationResult:
        result = ValidationResult()
        report = self.repository.report
        for txn_id in report.duplicates:
            result.findings.append(Finding("warning", "duplicate", "duplicate transaction id", txn_id))
        for txn_id in report.unknown_office:
            result.findings.append(Finding("error", "unknown-office", "office not in registry", txn_id))
        for error in report.rejected:
            result.findings.append(Finding("error", "decode", str(error)))
        transactions = self.repository.all()
        self._check_refunds(transactions, result)
        self._check_trading_hours(transactions, result)
        self._check_tills(transactions, result)
        result.per_day = self._per_day(transactions)
        return result

    def _check_refunds(self, transactions: list[Transaction], result: ValidationResult) -> None:
        refunded: dict[str, int] = defaultdict(int)
        for txn in transactions:
            if txn.kind is not Kind.REFUND:
                continue
            if not txn.reference:
                result.findings.append(Finding("warning", "refund-unlinked",
                                               "refund without original transaction", txn.txn_id))
                continue
            original = self.repository.get(txn.reference)
            if original is None:
                result.findings.append(Finding("warning", "refund-orphan",
                                               f"original {txn.reference} not found", txn.txn_id))
                continue
            if original.office != txn.office:
                result.findings.append(Finding("error", "refund-office",
                                               f"refunded at {txn.office}, sold at {original.office}",
                                               txn.txn_id))
            if txn.epoch < original.epoch:
                result.findings.append(Finding("error", "refund-before-sale",
                                               "refund processed before the sale", txn.txn_id))
            refunded[original.txn_id] += txn.amount.minor
            if refunded[original.txn_id] > original.amount.minor:
                result.findings.append(Finding("error", "over-refund",
                                               f"refunds exceed sale {original.txn_id}", txn.txn_id))

    def _check_trading_hours(self, transactions: list[Transaction], result: ValidationResult) -> None:
        for txn in transactions:
            if txn.kind is not Kind.SALE or txn.till == "WEB":
                continue
            office = self.offices.get(txn.office)
            if not office.is_trading_time(txn.at):
                wall = office.local(txn.at).strftime("%H:%M")
                result.findings.append(Finding("warning", "after-hours",
                                               f"sale at {wall} local outside trading hours",
                                               txn.txn_id))

    def _check_tills(self, transactions: list[Transaction], result: ValidationResult) -> None:
        for txn in transactions:
            office = self.offices.get(txn.office)
            if txn.till in ("PSP", "WEB"):
                continue
            if office.tills and txn.till not in office.tills:
                result.findings.append(Finding("warning", "unknown-till",
                                               f"till {txn.till!r} not registered for {office.code}",
                                               txn.txn_id))

    def _per_day(self, transactions: list[Transaction]) -> dict[str, dict[str, int]]:
        counts: dict[str, Counter] = defaultdict(Counter)
        for txn in transactions:
            office = self.offices.get(txn.office)
            day: date = txn.local_date(office.tz)
            counts[office.code][day.isoformat()] += 1
        return {code: dict(sorted(days.items())) for code, days in sorted(counts.items())}
