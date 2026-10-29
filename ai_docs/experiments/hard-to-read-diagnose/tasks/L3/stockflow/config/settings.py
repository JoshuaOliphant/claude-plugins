"""Application settings read from ``stockflow.ini``."""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from stockflow.domain.errors import ConfigError
from stockflow.utils.paths import PROJECT_ROOT, resolve

DEFAULT_CONFIG = PROJECT_ROOT / "stockflow.ini"
ENV_CONFIG = "STOCKFLOW_CONFIG"


@dataclass(frozen=True)
class Settings:
    config_path: Path
    catalog_path: Path
    units_path: Path
    opening_balances_path: Path
    default_workers: int
    file_pattern: str
    strict_catalog: bool
    allow_inactive_skus: bool
    max_errors_per_file: int
    low_stock_margin: int
    warehouses: tuple[str, ...]

    @property
    def base_dir(self) -> Path:
        return self.config_path.parent


def _read(path: Path) -> Settings:
    parser = configparser.ConfigParser()
    if not parser.read(path, encoding="utf-8"):
        raise ConfigError(f"configuration file not found: {path}")
    base = path.parent
    try:
        data = parser["data"]
        ingest = parser["ingest"]
        report = parser["report"]
        warehouses = tuple(
            w.strip().upper()
            for w in parser.get("warehouses", "codes", fallback="").split(",")
            if w.strip()
        )
        return Settings(
            config_path=path,
            catalog_path=resolve(base, data["catalog"]),
            units_path=resolve(base, data["units"]),
            opening_balances_path=resolve(base, data["opening_balances"]),
            default_workers=ingest.getint("workers", fallback=4),
            file_pattern=ingest.get("pattern", fallback="*.csv"),
            strict_catalog=ingest.getboolean("strict_catalog", fallback=True),
            allow_inactive_skus=ingest.getboolean("allow_inactive_skus", fallback=False),
            max_errors_per_file=ingest.getint("max_errors_per_file", fallback=50),
            low_stock_margin=report.getint("low_stock_margin", fallback=0),
            warehouses=warehouses,
        )
    except (KeyError, ValueError) as exc:
        raise ConfigError(f"invalid configuration in {path}: {exc}") from exc


_cached: Optional[Settings] = None
_cached_path: Optional[Path] = None


def load_settings(path: str | Path | None = None) -> Settings:
    """Load settings, reusing the last result for the same file."""
    global _cached, _cached_path
    if path is None:
        path = os.environ.get(ENV_CONFIG) or DEFAULT_CONFIG
    path = Path(path).resolve()
    if _cached is None or _cached_path != path:
        _cached = _read(path)
        _cached_path = path
    return _cached
