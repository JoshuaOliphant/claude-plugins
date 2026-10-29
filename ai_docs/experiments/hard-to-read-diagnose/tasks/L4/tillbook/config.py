"""Runtime configuration.

Settings come from ``config/settings.ini`` next to the package, optionally
overridden by a file named in ``TILLBOOK_CONFIG`` and by individual
``TILLBOOK_*`` environment variables.
"""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "settings.ini"


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    transactions_glob: str = "transactions/*.jsonl"
    refunds_file: str = "refunds.csv"
    offices_file: str = "offices.json"
    fx_file: str = "fx_rates.csv"
    archive_dir: Path | None = None
    report_currency: str = "USD"
    week_starts_on: int = 0
    cache_capacity: int = 256
    strict: bool = False
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def transactions_dir(self) -> Path:
        return self.data_dir

    def path(self, name: str) -> Path:
        return self.data_dir / name


_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


def _resolve(base: Path, value: str) -> Path:
    candidate = Path(value).expanduser()
    return candidate if candidate.is_absolute() else (base / candidate).resolve()


def load_settings(path: Path | None = None, env: dict[str, str] | None = None) -> Settings:
    env = dict(os.environ if env is None else env)
    parser = configparser.ConfigParser()
    parser.read(DEFAULT_CONFIG)
    override = path or (Path(env["TILLBOOK_CONFIG"]) if env.get("TILLBOOK_CONFIG") else None)
    if override is not None:
        if not override.exists():
            raise FileNotFoundError(f"config file not found: {override}")
        parser.read(override)
    section = parser["tillbook"] if parser.has_section("tillbook") else {}

    def pick(key: str, default: str) -> str:
        env_key = "TILLBOOK_" + key.upper()
        if env_key in env:
            return env[env_key]
        return section.get(key, default) if section else default

    data_dir = _resolve(PROJECT_ROOT, pick("data_dir", "data"))
    archive_value = pick("archive_dir", "")
    weekday_name = pick("week_starts_on", "monday").strip().lower()
    if weekday_name not in _WEEKDAYS:
        raise ValueError(f"unknown weekday in config: {weekday_name!r}")
    known = {
        "data_dir", "transactions_glob", "refunds_file", "offices_file", "fx_file",
        "archive_dir", "report_currency", "week_starts_on", "cache_capacity", "strict",
    }
    extra = {k: v for k, v in (section.items() if section else []) if k not in known}
    return Settings(
        data_dir=data_dir,
        transactions_glob=pick("transactions_glob", "transactions/*.jsonl"),
        refunds_file=pick("refunds_file", "refunds.csv"),
        offices_file=pick("offices_file", "offices.json"),
        fx_file=pick("fx_file", "fx_rates.csv"),
        archive_dir=_resolve(PROJECT_ROOT, archive_value) if archive_value else None,
        report_currency=pick("report_currency", "USD").upper(),
        week_starts_on=_WEEKDAYS[weekday_name],
        cache_capacity=int(pick("cache_capacity", "256")),
        strict=pick("strict", "false").strip().lower() in {"1", "true", "yes", "on"},
        extra=extra,
    )
