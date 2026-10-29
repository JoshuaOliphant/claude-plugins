"""Delivery date estimates."""

from __future__ import annotations

from datetime import date, timedelta

from freightdesk.pricing.tariffs import Tariff
from freightdesk.utils.holidays import SUPPORTED, add_business_days, is_business_day

CUTOFF_NOTE = "parcels handed over after the 16:00 cut-off ship the next business day"


def first_pickup_day(country: str, ship_date: date) -> date:
    day = ship_date
    while not is_business_day(country, day):
        day += timedelta(days=1)
    return day


def estimate_delivery(
    tariff: Tariff,
    zone: str,
    origin_country: str,
    dest_country: str,
    ship_date: date,
    service: str = "standard",
    saturday: bool = False,
) -> date | None:
    """Estimated delivery date, or None when the carrier publishes no transit time."""
    days = tariff.transit_days.get(zone)
    if days is None:
        return None
    if service == "express":
        days = max(1, days - 1)
    pickup = first_pickup_day(origin_country, ship_date)
    calendar = dest_country if dest_country in SUPPORTED else origin_country
    delivery = add_business_days(calendar, pickup, days)
    if saturday:
        # Saturday delivery lets a Monday arrival move forward to Saturday.
        previous = delivery - timedelta(days=1)
        while previous > pickup and not is_business_day(calendar, previous):
            if previous.weekday() == 5:
                return previous
            previous -= timedelta(days=1)
    return delivery
