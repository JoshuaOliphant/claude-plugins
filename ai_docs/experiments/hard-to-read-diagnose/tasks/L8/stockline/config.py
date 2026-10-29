"""Settings loaded from ``data/defaults.ini`` plus optional overrides.

Lookup order (later wins): packaged defaults, the file named by
``STOCKLINE_CONFIG`` or ``--config``, then individual ``STOCKLINE_*``
environment variables for the most commonly tweaked values.
"""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass, replace
from pathlib import Path

from stockline.domain.errors import ConfigError

PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULTS_PATH = PACKAGE_DIR / "data" / "defaults.ini"
DATA_DIR = PACKAGE_DIR / "data"


@dataclass(frozen=True)
class Settings:
    db_path: str
    currency: str
    progress_every: int
    max_reject_ratio: float
    min_rows_for_reject_check: int
    dedupe_window: int
    fuzzy_threshold: float
    allow_name_match: bool
    pricing_rules: Path
    categories: Path
    suppliers: Path

    def with_overrides(self, **values) -> "Settings":
        return replace(self, **values)


def _path(value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else DATA_DIR / p


def _read(parser: configparser.ConfigParser) -> Settings:
    try:
        imp = parser["import"]
        files = parser["files"]
        return Settings(
            db_path=parser.get("store", "path"),
            currency=parser.get("pricing", "currency"),
            progress_every=imp.getint("progress_every"),
            max_reject_ratio=imp.getfloat("max_reject_ratio"),
            min_rows_for_reject_check=imp.getint("min_rows_for_reject_check"),
            dedupe_window=imp.getint("dedupe_window"),
            fuzzy_threshold=imp.getfloat("fuzzy_threshold"),
            allow_name_match=imp.getboolean("allow_name_match"),
            pricing_rules=_path(files["pricing_rules"]),
            categories=_path(files["categories"]),
            suppliers=_path(files["suppliers"]),
        )
    except (KeyError, ValueError, configparser.Error) as exc:
        raise ConfigError(f"invalid configuration: {exc}") from exc


_ENV_OVERRIDES = {
    "STOCKLINE_DB": ("db_path", str),
    "STOCKLINE_PROGRESS_EVERY": ("progress_every", int),
    "STOCKLINE_MAX_REJECT_RATIO": ("max_reject_ratio", float),
}


def load_settings(path: str | os.PathLike | None = None, env: dict | None = None) -> Settings:
    env = os.environ if env is None else env
    parser = configparser.ConfigParser()
    if not parser.read(DEFAULTS_PATH, encoding="utf-8"):
        raise ConfigError(f"missing packaged defaults at {DEFAULTS_PATH}")
    extra = path or env.get("STOCKLINE_CONFIG")
    if extra:
        if not parser.read(extra, encoding="utf-8"):
            raise ConfigError(f"config file not found: {extra}")
    settings = _read(parser)
    overrides = {}
    for var, (attr, conv) in _ENV_OVERRIDES.items():
        if env.get(var):
            try:
                overrides[attr] = conv(env[var])
            except ValueError as exc:
                raise ConfigError(f"{var}: {exc}") from exc
    if overrides:
        settings = settings.with_overrides(**overrides)
    if settings.progress_every < 1:
        raise ConfigError("progress_every must be >= 1")
    return settings
