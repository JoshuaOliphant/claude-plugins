"""Zone assignment.

International zones come from the carrier's lane file
(``data/lanes/<code>.csv``).  Domestic shipments are zoned by the distance
between the leading routing digits of the origin and destination postcodes.
"""

from __future__ import annotations

import csv
from functools import lru_cache

from freightdesk.config import load_settings
from freightdesk.domain.errors import DataError, RatingError
from freightdesk.domain.shipment import Address
from freightdesk.utils.postcodes import region_digit

DOMESTIC = "domestic"


@lru_cache(maxsize=None)
def _lanes(carrier: str) -> dict[tuple[str, str], str]:
    path = load_settings().lanes_dir / f"{carrier.lower()}.csv"
    lanes: dict[tuple[str, str], str] = {}
    try:
        with path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                key = (row["origin"].strip().upper(), row["destination"].strip().upper())
                lanes[key] = row["zone"].strip()
    except FileNotFoundError:
        raise DataError(f"no lane file for carrier {carrier}") from None
    except KeyError as exc:
        raise DataError(f"{path.name}: missing column {exc}") from None
    return lanes


def domestic_zone(origin: Address, destination: Address) -> str:
    distance = abs(
        region_digit(origin.country, origin.postcode)
        - region_digit(destination.country, destination.postcode)
    )
    if distance == 0:
        return "1"
    if distance <= 3:
        return "2"
    return "3"


def zone_for(carrier: str, origin: Address, destination: Address) -> str:
    lane = _lanes(carrier.upper()).get((origin.country, destination.country))
    if lane is None:
        raise RatingError(
            f"{carrier} does not serve {origin.country} -> {destination.country}"
        )
    if lane == DOMESTIC:
        return domestic_zone(origin, destination)
    return lane


def served_lanes(carrier: str) -> list[tuple[str, str, str]]:
    return sorted((o, d, z) for (o, d), z in _lanes(carrier.upper()).items())
