"""Shipments, parcels and addresses."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from freightdesk.domain.errors import ValidationError
from freightdesk.utils.decimals import to_decimal
from freightdesk.utils.postcodes import PostcodeError, normalize_postcode

MAX_SIDE_CM = Decimal("300")
MAX_PARCEL_KG = Decimal("70")

_DIMS = re.compile(r"^\s*([\d.,]+)\s*[x*×]\s*([\d.,]+)\s*[x*×]\s*([\d.,]+)\s*(cm)?\s*$", re.I)
_PARCEL = re.compile(r"^(?P<dims>[^@]+)@(?P<weight>[\d.,]+)\s*(kg)?$", re.I)


@dataclass(frozen=True)
class Address:
    country: str
    postcode: str
    residential: bool = False

    @classmethod
    def parse(cls, country: str, postcode: str, residential: bool = False) -> "Address":
        country = country.strip().upper()
        try:
            normalised = normalize_postcode(country, postcode)
        except PostcodeError as exc:
            raise ValidationError(str(exc)) from exc
        return cls(country=country, postcode=normalised, residential=residential)

    def __str__(self) -> str:
        flag = " (residential)" if self.residential else ""
        return f"{self.country}-{self.postcode}{flag}"


@dataclass(frozen=True)
class Parcel:
    length_cm: Decimal
    width_cm: Decimal
    height_cm: Decimal
    weight_kg: Decimal

    def __post_init__(self):
        for name in ("length_cm", "width_cm", "height_cm"):
            value = getattr(self, name)
            if value <= 0 or value > MAX_SIDE_CM:
                raise ValidationError(f"{name.split('_')[0]} out of range: {value}")
        if self.weight_kg <= 0 or self.weight_kg > MAX_PARCEL_KG:
            raise ValidationError(f"weight out of range: {self.weight_kg}")

    @classmethod
    def from_strings(cls, dims: str, weight: str) -> "Parcel":
        match = _DIMS.match(dims)
        if not match:
            raise ValidationError(f"dimensions must look like 40x30x20, got {dims!r}")
        try:
            l, w, h = (to_decimal(g, "dimension") for g in match.groups()[:3])
            kg = to_decimal(weight, "weight")
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        return cls(length_cm=l, width_cm=w, height_cm=h, weight_kg=kg)

    @classmethod
    def parse(cls, spec: str) -> "Parcel":
        """Parse ``40x30x20@2.5`` (dimensions in cm, weight in kg)."""
        match = _PARCEL.match(spec.strip())
        if not match:
            raise ValidationError(f"parcel must look like 40x30x20@2.5, got {spec!r}")
        return cls.from_strings(match.group("dims"), match.group("weight"))

    @property
    def dims(self) -> tuple[Decimal, Decimal, Decimal]:
        return (self.length_cm, self.width_cm, self.height_cm)

    def describe(self) -> str:
        l, w, h = (format(d.normalize(), "f") for d in self.dims)
        return f"{l}x{w}x{h} cm, {format(self.weight_kg.normalize(), 'f')} kg"


@dataclass(frozen=True)
class Shipment:
    carrier: str
    origin: Address
    destination: Address
    parcels: tuple[Parcel, ...]
    ship_date: date
    service: str = "standard"
    reference: str = ""
    options: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self):
        if not self.parcels:
            raise ValidationError("a shipment needs at least one parcel")
        if self.service not in ("standard", "express"):
            raise ValidationError(f"unknown service {self.service!r}")

    @property
    def is_domestic(self) -> bool:
        return self.origin.country == self.destination.country

    @property
    def total_weight_kg(self) -> Decimal:
        return sum((p.weight_kg for p in self.parcels), Decimal(0))
