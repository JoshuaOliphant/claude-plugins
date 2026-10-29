"""Runtime configuration.

Settings come from ``data/settings.ini`` next to the package. A few values
can be overridden from the environment so that scripts and cron jobs can
point the tool at another database without editing the ini file.
"""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
DEFAULT_SETTINGS_FILE = PROJECT_ROOT / "data" / "settings.ini"

ENV_DB = "STOCKROOM_DB"
ENV_SETTINGS = "STOCKROOM_SETTINGS"
ENV_WAREHOUSE = "STOCKROOM_WAREHOUSE"


@dataclass(frozen=True)
class Settings:
    db_path: Path
    busy_timeout_ms: int
    default_warehouse: str
    allow_negative_on_hand: bool
    currency: str
    moves_window_days: int


_cached: Settings | None = None


def _resolve(path_text: str, base: Path) -> Path:
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = base / path
    return path


def load_settings(settings_file: Path | None = None) -> Settings:
    settings_file = settings_file or Path(os.environ.get(ENV_SETTINGS, DEFAULT_SETTINGS_FILE))
    parser = configparser.ConfigParser()
    parser.read_dict(
        {
            "database": {"path": "data/stockroom.db", "busy_timeout_ms": "2000"},
            "inventory": {"default_warehouse": "MAIN", "allow_negative_on_hand": "no"},
            "reports": {"currency": "USD", "moves_window_days": "30"},
        }
    )
    if settings_file.exists():
        parser.read(settings_file, encoding="utf-8")

    db_text = os.environ.get(ENV_DB) or parser.get("database", "path")
    db_base = Path.cwd() if os.environ.get(ENV_DB) else PROJECT_ROOT
    warehouse = os.environ.get(ENV_WAREHOUSE) or parser.get("inventory", "default_warehouse")

    return Settings(
        db_path=_resolve(db_text, db_base),
        busy_timeout_ms=parser.getint("database", "busy_timeout_ms"),
        default_warehouse=warehouse.strip().upper(),
        allow_negative_on_hand=parser.getboolean("inventory", "allow_negative_on_hand"),
        currency=parser.get("reports", "currency").strip().upper(),
        moves_window_days=parser.getint("reports", "moves_window_days"),
    )


def get_settings() -> Settings:
    """Return process-wide settings, loading them on first use."""
    global _cached
    if _cached is None:
        _cached = load_settings()
    return _cached


def override(**changes) -> Settings:
    """Replace selected settings for the rest of the process (used by the CLI)."""
    global _cached
    current = get_settings()
    values = {**current.__dict__, **{k: v for k, v in changes.items() if v is not None}}
    _cached = Settings(**values)
    return _cached
