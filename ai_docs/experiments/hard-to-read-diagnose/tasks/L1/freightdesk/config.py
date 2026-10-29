"""Runtime configuration.

Settings are read from ``etc/freightdesk.ini`` under the installation home
(the directory that contains the ``freightdesk`` package) and may be
overridden with environment variables:

``FREIGHTDESK_HOME``       installation home
``FREIGHTDESK_CACHE_DIR``  location of the persistent result cache
``FREIGHTDESK_LOG_LEVEL``  logging level name
"""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_HOME = PACKAGE_DIR.parent


@dataclass(frozen=True)
class Settings:
    home: Path
    data_dir: Path
    cache_dir: Path
    default_carrier: str
    default_currency: str
    origin_country: str
    origin_postcode: str
    log_level: str

    @property
    def tariff_dir(self) -> Path:
        return self.data_dir / "tariffs"

    @property
    def lanes_dir(self) -> Path:
        return self.data_dir / "lanes"

    @property
    def fx_file(self) -> Path:
        return self.data_dir / "fx" / "eurofxref-hist.csv"


_settings: Settings | None = None


def _resolve(home: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = home / path
    return path


def load_settings(reload: bool = False) -> Settings:
    """Return process-wide settings, reading the ini file on first use."""
    global _settings
    if _settings is not None and not reload:
        return _settings

    home = Path(os.environ.get("FREIGHTDESK_HOME", DEFAULT_HOME)).resolve()
    parser = configparser.ConfigParser()
    parser.read_dict(
        {
            "paths": {"data_dir": "data", "cache_dir": "var/cache"},
            "defaults": {
                "carrier": "NORDLINE",
                "currency": "EUR",
                "origin_country": "DE",
                "origin_postcode": "10115",
            },
            "logging": {"level": "WARNING"},
        }
    )
    parser.read(home / "etc" / "freightdesk.ini", encoding="utf-8")

    cache_dir = os.environ.get("FREIGHTDESK_CACHE_DIR") or parser.get("paths", "cache_dir")
    _settings = Settings(
        home=home,
        data_dir=_resolve(home, parser.get("paths", "data_dir")),
        cache_dir=_resolve(home, cache_dir),
        default_carrier=parser.get("defaults", "carrier").upper(),
        default_currency=parser.get("defaults", "currency").upper(),
        origin_country=parser.get("defaults", "origin_country").upper(),
        origin_postcode=parser.get("defaults", "origin_postcode"),
        log_level=os.environ.get("FREIGHTDESK_LOG_LEVEL", parser.get("logging", "level")).upper(),
    )
    return _settings
