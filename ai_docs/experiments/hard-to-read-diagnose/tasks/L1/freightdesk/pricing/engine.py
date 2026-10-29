"""The rating engine: turns a shipment into priced quote lines.

Pricing order (per the carriers' general terms):

1. each parcel is measured and priced from its zone's weight band;
2. express service multiplies the base freight;
3. parcel surcharges (oversize, heavy) are added per parcel;
4. shipment surcharges (residential, remote, customs, Saturday) once;
5. the fuel surcharge is a percentage of base freight plus surcharges.
"""

from __future__ import annotations

from decimal import Decimal

from freightdesk.domain.errors import RatingError
from freightdesk.domain.money import Money
from freightdesk.domain.quote import ParcelRating, Quote, QuoteLine
from freightdesk.domain.shipment import Parcel, Shipment
from freightdesk.pricing import surcharges
from freightdesk.pricing.dimensions import profile_parcel
from freightdesk.pricing.tariffs import Tariff, get_tariff
from freightdesk.pricing.zones import zone_for
from freightdesk.utils.decimals import percent_of, to_decimal
from freightdesk.utils.log import get_logger

log = get_logger(__name__)


class RatingEngine:
    def __init__(self, tariff_loader=get_tariff):
        self._load = tariff_loader

    def price(self, shipment: Shipment) -> Quote:
        tariff = self._load(shipment.carrier)
        zone = zone_for(tariff.code, shipment.origin, shipment.destination)
        quote = Quote(
            carrier=tariff.code,
            tariff_revision=tariff.revision,
            service=shipment.service,
            zone=zone,
            currency=tariff.currency,
            reference=shipment.reference,
        )

        for index, parcel in enumerate(shipment.parcels, start=1):
            self._price_parcel(tariff, shipment, zone, index, parcel, quote)

        for sur in surcharges.shipment_surcharges(tariff, shipment):
            quote.lines.append(QuoteLine(sur.code, sur.description, Money(sur.amount, tariff.currency)))

        if tariff.fuel_surcharge_pct:
            fuel_base = quote.total.amount
            quote.lines.append(
                QuoteLine(
                    "FUEL",
                    f"Fuel surcharge {tariff.fuel_surcharge_pct}%",
                    Money(percent_of(fuel_base, tariff.fuel_surcharge_pct), tariff.currency),
                )
            )
        log.debug("rated %s: %s", shipment.reference or "shipment", quote.total)
        return quote

    def _price_parcel(
        self,
        tariff: Tariff,
        shipment: Shipment,
        zone: str,
        index: int,
        parcel: Parcel,
        quote: Quote,
    ) -> None:
        profile = profile_parcel(
            tariff.code, parcel.length_cm, parcel.width_cm, parcel.height_cm, parcel.weight_kg
        )
        billable = to_decimal(profile["billable_kg"])
        if billable > tariff.max_weight_kg:
            raise RatingError(
                f"parcel {index}: billable weight {billable} kg exceeds "
                f"{tariff.code} limit of {tariff.max_weight_kg} kg"
            )
        band = tariff.band_for(zone, billable)
        base = band.price
        description = f"Freight zone {zone}, up to {band.upper_kg} kg"
        if shipment.service == "express":
            base = base * tariff.express_multiplier
            description += " (express)"
        quote.lines.append(QuoteLine("BASE", description, Money(base, tariff.currency), index))
        quote.parcels.append(
            ParcelRating(
                index=index,
                zone=zone,
                actual_kg=parcel.weight_kg,
                dim_weight_kg=to_decimal(profile["dim_weight_kg"]),
                billable_kg=billable,
                band_kg=band.upper_kg,
            )
        )

        facts = surcharges.ParcelFacts(
            index=index,
            longest_cm=to_decimal(profile["longest_cm"]),
            girth_cm=to_decimal(profile["girth_cm"]),
            billable_kg=billable,
        )
        for sur in surcharges.parcel_surcharges(tariff, shipment, facts):
            quote.lines.append(
                QuoteLine(sur.code, sur.description, Money(sur.amount, tariff.currency), sur.parcel_index)
            )


def billable_total(quote: Quote) -> Decimal:
    return sum((p.billable_kg for p in quote.parcels), Decimal(0))
