"""Application settings, read from ``config/ledgerly.toml``.

The file location can be overridden with the ``LEDGERLY_CONFIG`` environment
variable. Paths inside the file are resolved relative to the project root.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Mapping

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "ledgerly.toml"
ENV_VAR = "LEDGERLY_CONFIG"


class ConfigError(Exception):
    """Raised for a missing or malformed settings file."""


@dataclass(frozen=True)
class Settings:
    base_currency: str
    due_days: int
    default_region: str
    tax_rates: Mapping[str, Decimal]
    top_customers: int
    aging_buckets: tuple[int, ...]
    data_dir: Path
    customers_file: Path
    fx_rates_file: Path
    forecast_window: int = 3
    extras: Mapping[str, object] = field(default_factory=dict)


def _resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (root / path)


def _parse(raw: dict, root: Path) -> Settings:
    try:
        ledger = raw["ledger"]
        tax = raw["tax"]
        report = raw.get("report", {})
        paths = raw.get("paths", {})
    except KeyError as exc:
        raise ConfigError(f"missing section: {exc.args[0]}") from None

    rates = {region.upper(): Decimal(str(rate)) for region, rate in tax.get("rates", {}).items()}
    default_region = tax.get("default_region", "").upper()
    if default_region and default_region not in rates:
        raise ConfigError(f"default_region {default_region!r} has no rate")

    buckets = tuple(sorted(int(b) for b in report.get("aging_buckets", (30, 60, 90))))
    data_dir = _resolve(root, paths.get("data_dir", "data"))
    known = {"ledger", "tax", "report", "paths"}
    return Settings(
        base_currency=ledger.get("base_currency", "USD").upper(),
        due_days=int(ledger.get("due_days", 30)),
        default_region=default_region,
        tax_rates=rates,
        top_customers=int(report.get("top_customers", 5)),
        aging_buckets=buckets,
        data_dir=data_dir,
        customers_file=_resolve(data_dir, paths.get("customers", "customers.json")),
        fx_rates_file=_resolve(data_dir, paths.get("fx_rates", "fx_rates.json")),
        forecast_window=int(report.get("forecast_window", 3)),
        extras={k: v for k, v in raw.items() if k not in known},
    )


@lru_cache(maxsize=4)
def load(path: str | None = None) -> Settings:
    """Load settings once per path; later calls return the cached object."""
    chosen = Path(path or os.environ.get(ENV_VAR) or DEFAULT_CONFIG)
    try:
        with chosen.open("rb") as handle:
            raw = tomllib.load(handle)
    except FileNotFoundError:
        raise ConfigError(f"settings file not found: {chosen}") from None
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{chosen}: {exc}") from None
    return _parse(raw, PROJECT_ROOT)
