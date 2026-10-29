"""Quote results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from freightdesk.domain.money import Money, total
from freightdesk.utils.decimals import plain


@dataclass(frozen=True)
class QuoteLine:
    code: str
    description: str
    amount: Money
    parcel_index: int | None = None

    def to_json(self) -> dict:
        data = {"code": self.code, "description": self.description, **self.amount.to_json()}
        if self.parcel_index is not None:
            data["parcel"] = self.parcel_index
        return data


@dataclass(frozen=True)
class ParcelRating:
    index: int
    zone: str
    actual_kg: Decimal
    dim_weight_kg: Decimal
    billable_kg: Decimal
    band_kg: Decimal

    def to_json(self) -> dict:
        return {
            "parcel": self.index,
            "zone": self.zone,
            "actual_kg": plain(self.actual_kg),
            "dim_weight_kg": plain(self.dim_weight_kg),
            "billable_kg": plain(self.billable_kg),
            "band_kg": plain(self.band_kg),
        }


@dataclass
class Quote:
    carrier: str
    tariff_revision: str
    service: str
    zone: str
    currency: str
    lines: list[QuoteLine] = field(default_factory=list)
    parcels: list[ParcelRating] = field(default_factory=list)
    estimated_delivery: date | None = None
    reference: str = ""
    fx_rate: Decimal | None = None

    @property
    def total(self) -> Money:
        return total((line.amount for line in self.lines), self.currency)

    def subtotal(self, code_prefix: str) -> Money:
        return total(
            (line.amount for line in self.lines if line.code.startswith(code_prefix)),
            self.currency,
        )

    def to_json(self) -> dict:
        data = {
            "carrier": self.carrier,
            "tariff_revision": self.tariff_revision,
            "service": self.service,
            "zone": self.zone,
            "reference": self.reference,
            "parcels": [p.to_json() for p in self.parcels],
            "lines": [line.to_json() for line in self.lines],
            "total": self.total.to_json(),
            "estimated_delivery": self.estimated_delivery.isoformat() if self.estimated_delivery else None,
        }
        if self.fx_rate is not None:
            data["fx_rate"] = plain(self.fx_rate)
        return data
