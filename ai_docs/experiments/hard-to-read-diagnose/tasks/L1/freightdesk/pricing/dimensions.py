"""Parcel measurement: volume, girth and dimensional ("volumetric") weight.

Carriers bill the greater of the actual weight and the dimensional weight
``L x W x H / divisor``, rounded up to the carrier's weight step.
"""

from __future__ import annotations

from decimal import Decimal

from freightdesk.pricing.tariffs import get_tariff
from freightdesk.utils.decimals import quantize, round_up_to_step, to_decimal
from freightdesk.utils.diskcache import memoize_to_disk


def girth_cm(length: Decimal, width: Decimal, height: Decimal) -> Decimal:
    """Longest side plus the circumference around the other two."""
    sides = sorted((length, width, height), reverse=True)
    return sides[0] + 2 * (sides[1] + sides[2])


@memoize_to_disk("parcel-profile")
def profile_parcel(carrier: str, length_cm, width_cm, height_cm, weight_kg) -> dict:
    """Measure one parcel for ``carrier``.

    Returns a JSON-friendly dict of decimal strings: ``volume_cm3``,
    ``longest_cm``, ``girth_cm``, ``dim_weight_kg`` and ``billable_kg``.
    """
    tariff = get_tariff(carrier)
    length = to_decimal(length_cm, "length")
    width = to_decimal(width_cm, "width")
    height = to_decimal(height_cm, "height")
    actual = to_decimal(weight_kg, "weight")

    volume = length * width * height
    dim_weight = quantize(volume / tariff.dim_divisor, "0.01")
    billable = round_up_to_step(max(actual, dim_weight), tariff.weight_step_kg)
    return {
        "volume_cm3": format(volume.normalize(), "f"),
        "longest_cm": format(max(length, width, height).normalize(), "f"),
        "girth_cm": format(girth_cm(length, width, height).normalize(), "f"),
        "dim_weight_kg": format(dim_weight.normalize(), "f"),
        "billable_kg": format(billable.normalize(), "f"),
    }
