"""Turn raw source records into ledger transactions."""

from __future__ import annotations

import re

from ledgerflow.categorize import Categorizer
from ledgerflow.fx import FxError, RateTable
from ledgerflow.models import Transaction
from ledgerflow.money import Money, MoneyError, parse_amount, quantize
from ledgerflow.sources.base import RawRecord
from ledgerflow.utils.dates import DateError, parse_date

_SPACES = re.compile(r"\s+")


class NormalizationError(ValueError):
    def __init__(self, record_id: str, reasons: list[str]):
        super().__init__(f"{record_id}: {'; '.join(reasons)}")
        self.record_id = record_id
        self.reasons = reasons


def clean_memo(memo: str) -> str:
    return _SPACES.sub(" ", memo).strip().upper()


class Normalizer:
    def __init__(self, rates: RateTable, categorizer: Categorizer, base_currency: str):
        self.rates = rates
        self.categorizer = categorizer
        self.base_currency = base_currency

    def normalize(self, record: RawRecord, source: str) -> Transaction:
        reasons = [f"missing {name}" for name in record.missing()]
        if reasons:
            raise NormalizationError(record.record_id or f"line {record.line}", reasons)
        try:
            posted = parse_date(record.posted, record.date_format)
        except DateError as exc:
            reasons.append(str(exc))
        try:
            value = parse_amount(record.amount)
        except MoneyError as exc:
            reasons.append(str(exc))
        if reasons:
            raise NormalizationError(record.record_id, reasons)

        try:
            amount = Money(quantize(value, record.currency), record.currency)
            amount_base = self.rates.convert(amount, self.base_currency, posted)
        except (MoneyError, FxError) as exc:
            raise NormalizationError(record.record_id, [str(exc)]) from exc

        memo = clean_memo(record.memo)
        return Transaction(
            txn_id=record.record_id,
            posted=posted,
            amount=amount,
            amount_base=amount_base,
            account=record.account,
            memo=memo,
            category=self.categorizer.categorize(memo, record.account, amount.amount),
            source=source,
        )
