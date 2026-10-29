"""Layered configuration.

Settings are resolved from, lowest to highest precedence:

1. built-in defaults,
2. every ``*.ini`` file in the configuration directory, applied in
   lexical order so ``50-site.ini`` overrides ``10-defaults.ini``,
3. ``LEDGERKIT_<SECTION>_<KEY>`` environment variables.
"""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULTS: dict[str, dict[str, str]] = {
    "ledger": {
        "currency": "USD",
    },
    "export": {
        "default_format": "csv",
        "date_format": "",
        "columns": "date,payee,account,category,amount,currency,memo",
    },
    "display": {
        "locale": "C",
        "title": "Ledger report",
    },
    "validation": {
        "categories": "",
        "max_future_days": "0",
        "allow_zero": "false",
    },
}

ENV_PREFIX = "LEDGERKIT_"


def default_config_dir() -> Path:
    env = os.environ.get("LEDGERKIT_CONF_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "conf.d"


@dataclass
class Config:
    values: dict[str, dict[str, str]] = field(default_factory=dict)
    sources: list[str] = field(default_factory=list)

    def get(self, section: str, key: str, fallback: str | None = None) -> str | None:
        return self.values.get(section, {}).get(key, fallback)

    def get_bool(self, section: str, key: str, fallback: bool = False) -> bool:
        raw = self.get(section, key)
        if raw is None:
            return fallback
        return raw.strip().lower() in {"1", "true", "yes", "on"}

    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        raw = self.get(section, key)
        try:
            return int(raw) if raw is not None else fallback
        except ValueError:
            return fallback

    def get_list(self, section: str, key: str) -> list[str]:
        raw = self.get(section, key) or ""
        return [item.strip() for item in raw.split(",") if item.strip()]

    def set(self, section: str, key: str, value: str) -> None:
        self.values.setdefault(section, {})[key] = value


def _config_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.iterdir() if p.suffix == ".ini" and p.is_file())


def load_config(directory: Path | str | None = None, environ=None) -> Config:
    environ = os.environ if environ is None else environ
    cfg = Config({section: dict(keys) for section, keys in DEFAULTS.items()})
    directory = Path(directory) if directory else default_config_dir()
    for path in _config_files(directory):
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(path, encoding="utf-8")
        for section in parser.sections():
            for key, value in parser.items(section):
                cfg.set(section, key, value)
        cfg.sources.append(str(path))
    for name, value in environ.items():
        if not name.startswith(ENV_PREFIX) or name == "LEDGERKIT_CONF_DIR":
            continue
        rest = name[len(ENV_PREFIX):].lower()
        section, sep, key = rest.partition("_")
        if sep and section in cfg.values:
            cfg.set(section, key, value)
    return cfg
