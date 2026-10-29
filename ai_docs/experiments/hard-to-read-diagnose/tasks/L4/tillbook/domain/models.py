"""Transaction and report row types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum

from tillbook.domain.money import Money


class Kind(str, Enum):
    SALE = "sale"
    REFUND = "refund"
    VOID = "void"


class Tender(str, Enum):
    CARD = "card"
    CASH = "cash"
    UPI = "upi"
    WALLET = "wallet"
    VOUCHER = "voucher"

    @classmethod
    def parse(cls, value: str) -> "Tender":
        try:
            return cls(value.strip().lower())
        except ValueError:
            raise ValueError(f"unknown tender {value!r}") from None


@dataclass(frozen=True)
class LineItem:
    sku: str
    description: str
    quantity: int
    unit_price: Money

    @property
    def amount(self) -> Money:
        return Money(self.unit_price.minor * self.quantity, self.unit_price.currency)


@dataclass(frozen=True)
class Transaction:
    """One till event.

    ``epoch`` is the capture instant in UTC seconds and is what the storage
    layer sorts and indexes on; ``at`` is the same instant as an aware
    datetime for convenience.
    """

    txn_id: str
    office: str
    till: str
    kind: Kind
    tender: Tender
    epoch: int
    at: datetime
    amount: Money
    items: tuple[LineItem, ...] = ()
    reference: str | None = None
    source: str = ""

    @property
    def signed_amount(self) -> Money:
        if self.kind is Kind.REFUND:
            return -self.amount
        if self.kind is Kind.VOID:
            return Money.zero(self.amount.currency)
        return self.amount

    def local_date(self, tz) -> date:
        return self.at.astimezone(tz).date()


@dataclass
class DailyTotal:
    office: str
    day: date
    currency: str
    sales_count: int = 0
    refund_count: int = 0
    void_count: int = 0
    gross: Money | None = None
    refunds: Money | None = None
    by_tender: dict[str, Money] = field(default_factory=dict)
    first_sale: datetime | None = None
    last_sale: datetime | None = None

    def __post_init__(self) -> None:
        if self.gross is None:
            self.gross = Money.zero(self.currency)
        if self.refunds is None:
            self.refunds = Money.zero(self.currency)

    @property
    def net(self) -> Money:
        return self.gross - self.refunds

    @property
    def transaction_count(self) -> int:
        return self.sales_count + self.refund_count + self.void_count

    def to_json(self) -> dict:
        return {
            "office": self.office,
            "date": self.day.isoformat(),
            "currency": self.currency,
            "sales": self.sales_count,
            "refunds": self.refund_count,
            "voids": self.void_count,
            "gross": self.gross.to_json(),
            "refunded": self.refunds.to_json(),
            "net": self.net.to_json(),
            "by_tender": {k: v.to_json() for k, v in sorted(self.by_tender.items())},
        }


@dataclass
class ItemTotal:
    sku: str
    description: str
    quantity: int
    revenue: Money

    def to_json(self) -> dict:
        return {
            "sku": self.sku,
            "description": self.description,
            "quantity": self.quantity,
            "revenue": self.revenue.to_json(),
        }
