"""Application settings.

Settings are read from ``data/settings.json`` and may be partially overridden
by a JSON file named in the ``BASKETRY_SETTINGS`` environment variable.  The
result is frozen so that no request can modify shared configuration.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from .utils.mapping import deep_merge, freeze, require_path

PACKAGE_DIR = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_DIR / "data"
SETTINGS_ENV = "BASKETRY_SETTINGS"
DATA_DIR_ENV = "BASKETRY_DATA_DIR"


@dataclass(frozen=True)
class ShippingRate:
    base_cents: int
    per_kg_cents: int


@dataclass(frozen=True)
class Settings:
    currency: str
    free_shipping_over_cents: int
    shipping_rates: MappingProxyType
    box_capacity_grams: int
    box_tare_grams: int
    sample_threshold_cents: int
    sample_sku: str
    gift_wrap_fee_cents: int
    tier_discount_bps: MappingProxyType
    tax_rates_bps: MappingProxyType
    raw: MappingProxyType

    def shipping_rate(self, speed: str) -> ShippingRate:
        try:
            rate = self.shipping_rates[speed]
        except KeyError:
            raise KeyError(f"no shipping rate configured for speed {speed!r}") from None
        return ShippingRate(base_cents=rate["base_cents"], per_kg_cents=rate["per_kg_cents"])

    def tier_discount(self, tier: str) -> int:
        return int(self.tier_discount_bps.get(tier, 0))


def data_dir() -> Path:
    override = os.environ.get(DATA_DIR_ENV)
    return Path(override) if override else DATA_DIR


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def load_settings(path: Path | None = None) -> Settings:
    base = _read_json(path or data_dir() / "settings.json")
    override_path = os.environ.get(SETTINGS_ENV)
    if override_path:
        base = deep_merge(base, _read_json(Path(override_path)))
    frozen = freeze(base)
    return Settings(
        currency=require_path(frozen, "currency"),
        free_shipping_over_cents=require_path(frozen, "shipping.free_over_cents"),
        shipping_rates=require_path(frozen, "shipping.rates"),
        box_capacity_grams=require_path(frozen, "packing.box_capacity_grams"),
        box_tare_grams=require_path(frozen, "packing.box_tare_grams"),
        sample_threshold_cents=require_path(frozen, "packing.sample_threshold_cents"),
        sample_sku=require_path(frozen, "packing.sample_sku"),
        gift_wrap_fee_cents=require_path(frozen, "gift_wrap.fee_cents"),
        tier_discount_bps=MappingProxyType(
            {tier: spec["discount_bps"] for tier, spec in require_path(frozen, "tiers").items()}
        ),
        tax_rates_bps=require_path(frozen, "tax"),
        raw=frozen,
    )
