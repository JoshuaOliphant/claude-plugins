"""Carrier tariff loading.

Each carrier publishes a rate card that we keep as ``data/tariffs/<code>.json``.
Rate cards are replaced wholesale when a carrier issues a new revision; the
``revision`` field identifies the published card.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from freightdesk.config import load_settings
from freightdesk.domain.errors import DataError
from freightdesk.utils.decimals import to_decimal


@dataclass(frozen=True)
class WeightBand:
    upper_kg: Decimal
    price: Decimal


@dataclass(frozen=True)
class Tariff:
    code: str
    name: str
    currency: str
    revision: str
    dim_divisor: Decimal
    weight_step_kg: Decimal
    max_weight_kg: Decimal
    fuel_surcharge_pct: Decimal
    express_multiplier: Decimal
    bands: dict[str, tuple[WeightBand, ...]]
    transit_days: dict[str, int]
    surcharges: dict[str, Decimal]
    oversize_longest_cm: Decimal
    oversize_girth_cm: Decimal
    remote_postcodes: frozenset[str] = field(default_factory=frozenset)

    def band_for(self, zone: str, billable_kg: Decimal) -> WeightBand:
        try:
            bands = self.bands[zone]
        except KeyError:
            raise DataError(f"{self.code} has no prices for zone {zone}") from None
        for band in bands:
            if billable_kg <= band.upper_kg:
                return band
        raise DataError(f"{self.code} zone {zone} has no band for {billable_kg} kg")

    def surcharge(self, name: str) -> Decimal:
        return self.surcharges.get(name, Decimal(0))


def _parse(raw: dict, source: Path) -> Tariff:
    try:
        bands = {
            str(zone): tuple(
                WeightBand(to_decimal(upper, "band"), to_decimal(price, "price"))
                for upper, price in rows
            )
            for zone, rows in raw["zones"].items()
        }
        for zone, rows in bands.items():
            uppers = [b.upper_kg for b in rows]
            if uppers != sorted(uppers):
                raise DataError(f"{source.name}: zone {zone} bands are not ascending")
        surcharges = {k: to_decimal(v, k) for k, v in raw.get("surcharges", {}).items()}
        oversize = raw.get("oversize", {})
        return Tariff(
            code=raw["code"].upper(),
            name=raw["name"],
            currency=raw.get("currency", "EUR"),
            revision=raw["revision"],
            dim_divisor=to_decimal(raw["dim_divisor"], "dim_divisor"),
            weight_step_kg=to_decimal(raw.get("weight_step_kg", "0.5"), "weight_step_kg"),
            max_weight_kg=to_decimal(raw["max_weight_kg"], "max_weight_kg"),
            fuel_surcharge_pct=to_decimal(raw.get("fuel_surcharge_pct", "0"), "fuel"),
            express_multiplier=to_decimal(raw.get("express_multiplier", "1.6"), "express"),
            bands=bands,
            transit_days={str(k): int(v) for k, v in raw["transit_days"].items()},
            surcharges=surcharges,
            oversize_longest_cm=to_decimal(oversize.get("longest_cm", "120"), "oversize"),
            oversize_girth_cm=to_decimal(oversize.get("girth_cm", "300"), "oversize"),
            remote_postcodes=frozenset(raw.get("remote_postcodes", [])),
        )
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, DataError):
            raise
        raise DataError(f"malformed tariff {source.name}: {exc}") from exc


_LOADED: dict[str, Tariff] = {}


def available_carriers() -> list[str]:
    tariff_dir = load_settings().tariff_dir
    return sorted(p.stem.upper() for p in tariff_dir.glob("*.json"))


def get_tariff(code: str) -> Tariff:
    """Load (once per process) and return the current tariff for ``code``."""
    code = code.upper()
    tariff = _LOADED.get(code)
    if tariff is not None:
        return tariff
    path = load_settings().tariff_dir / f"{code.lower()}.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise DataError(f"unknown carrier {code!r}") from None
    except ValueError as exc:
        raise DataError(f"malformed tariff {path.name}: {exc}") from exc
    tariff = _parse(raw, path)
    _LOADED[code] = tariff
    return tariff
