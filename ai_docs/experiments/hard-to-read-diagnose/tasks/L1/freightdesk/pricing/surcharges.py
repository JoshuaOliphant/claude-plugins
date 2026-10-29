"""Surcharge rules applied on top of the base freight."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Callable

from freightdesk.domain.shipment import Shipment
from freightdesk.pricing.tariffs import Tariff


@dataclass(frozen=True)
class ParcelFacts:
    index: int
    longest_cm: Decimal
    girth_cm: Decimal
    billable_kg: Decimal


@dataclass(frozen=True)
class Surcharge:
    code: str
    description: str
    amount: Decimal
    parcel_index: int | None = None


ParcelRule = Callable[[Tariff, Shipment, ParcelFacts], Surcharge | None]
ShipmentRule = Callable[[Tariff, Shipment], Surcharge | None]


def oversize(tariff: Tariff, shipment: Shipment, facts: ParcelFacts) -> Surcharge | None:
    if facts.longest_cm > tariff.oversize_longest_cm or facts.girth_cm > tariff.oversize_girth_cm:
        return Surcharge(
            "SUR-OVERSIZE",
            f"Oversize parcel (longest {facts.longest_cm} cm, girth {facts.girth_cm} cm)",
            tariff.surcharge("oversize"),
            facts.index,
        )
    return None


def heavy(tariff: Tariff, shipment: Shipment, facts: ParcelFacts) -> Surcharge | None:
    threshold = tariff.surcharges.get("heavy_threshold_kg")
    if threshold is not None and facts.billable_kg > threshold:
        return Surcharge("SUR-HEAVY", "Heavy parcel handling", tariff.surcharge("heavy"), facts.index)
    return None


def residential(tariff: Tariff, shipment: Shipment) -> Surcharge | None:
    if shipment.destination.residential and tariff.surcharge("residential"):
        return Surcharge("SUR-RESI", "Residential delivery", tariff.surcharge("residential"))
    return None


def remote_area(tariff: Tariff, shipment: Shipment) -> Surcharge | None:
    if shipment.destination.postcode in tariff.remote_postcodes:
        return Surcharge("SUR-REMOTE", "Remote / island delivery", tariff.surcharge("remote"))
    return None


def customs(tariff: Tariff, shipment: Shipment) -> Surcharge | None:
    if shipment.destination.country == "CH" and shipment.origin.country != "CH":
        return Surcharge("SUR-CUSTOMS", "Customs clearance (non-EU)", tariff.surcharge("customs"))
    return None


def saturday(tariff: Tariff, shipment: Shipment) -> Surcharge | None:
    if "saturday" in shipment.options:
        return Surcharge("SUR-SAT", "Saturday delivery", tariff.surcharge("saturday"))
    return None


PARCEL_RULES: tuple[ParcelRule, ...] = (oversize, heavy)
SHIPMENT_RULES: tuple[ShipmentRule, ...] = (residential, remote_area, customs, saturday)


def parcel_surcharges(tariff: Tariff, shipment: Shipment, facts: ParcelFacts) -> list[Surcharge]:
    return [s for rule in PARCEL_RULES if (s := rule(tariff, shipment, facts)) and s.amount]


def shipment_surcharges(tariff: Tariff, shipment: Shipment) -> list[Surcharge]:
    return [s for rule in SHIPMENT_RULES if (s := rule(tariff, shipment)) and s.amount]
