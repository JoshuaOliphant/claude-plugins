"""Customer directory backed by ``customers.json``."""

from __future__ import annotations

import json
from pathlib import Path

from ..domain.customer import Customer


class UnknownCustomer(LookupError):
    def __init__(self, customer_id: str):
        super().__init__(f"unknown customer {customer_id!r}")
        self.customer_id = customer_id


class CustomerStore:
    """Lookup of customer records.

    Records are loaded lazily on first access and kept for the life of the
    store; the same ``Customer`` instance is returned for repeat lookups.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self._by_id: dict[str, Customer] | None = None
        self.lookups = 0

    def _index(self) -> dict[str, Customer]:
        if self._by_id is None:
            with self.path.open(encoding="utf-8") as fh:
                raw = json.load(fh)
            self._by_id = {}
            for entry in raw["customers"]:
                customer = Customer.from_dict(entry)
                self._by_id[customer.customer_id] = customer
        return self._by_id

    def get(self, customer_id: str) -> Customer:
        self.lookups += 1
        try:
            return self._index()[customer_id]
        except KeyError:
            raise UnknownCustomer(customer_id) from None

    def all(self) -> list[Customer]:
        return sorted(self._index().values(), key=lambda c: c.customer_id)

    def by_tier(self, tier: str) -> list[Customer]:
        return [c for c in self.all() if c.tier == tier]

    def reload(self) -> None:
        self._by_id = None
