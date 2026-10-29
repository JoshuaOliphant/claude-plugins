"""Calendar-aware queries over the transaction repository."""

from __future__ import annotations

from datetime import date

from tillbook.domain.models import Kind, Transaction
from tillbook.domain.offices import Office
from tillbook.storage.repository import TransactionRepository
from tillbook.utils.cache import BoundedCache
from tillbook.utils.timeconv import date_range


class LedgerService:
    def __init__(self, repository: TransactionRepository, cache_capacity: int = 256) -> None:
        self.repository = repository
        self.offices = repository.offices
        self._days: BoundedCache[tuple[Transaction, ...]] = BoundedCache(cache_capacity)

    def office(self, code: str) -> Office:
        return self.offices.get(code)

    def transactions_on(self, office_code: str, day: date) -> tuple[Transaction, ...]:
        """All transactions captured during ``day`` in the office's calendar."""
        office = self.office(office_code)
        key = (office.code, day.isoformat())

        def load() -> tuple[Transaction, ...]:
            start, end = office.day_bounds(day)
            return tuple(self.repository.index(office.code).between(start, end))

        return self._days.get_or_compute(key, load)

    def transactions_between(self, office_code: str, first: date, last: date
                             ) -> dict[date, tuple[Transaction, ...]]:
        return {day: self.transactions_on(office_code, day) for day in date_range(first, last)}

    def sales_on(self, office_code: str, day: date) -> list[Transaction]:
        return [t for t in self.transactions_on(office_code, day) if t.kind is Kind.SALE]

    def trading_days(self, office_code: str) -> list[date]:
        """Every office-local date that has at least one transaction."""
        office = self.office(office_code)
        days = {txn.local_date(office.tz) for txn in self.repository.index(office.code)}
        return sorted(days)

    def invalidate(self, office_code: str | None = None) -> int:
        if office_code is None:
            return self._days.invalidate()
        code = self.office(office_code).code
        return self._days.invalidate(lambda key: key[0] == code)

    def cache_stats(self) -> dict[str, int]:
        return self._days.stats()
