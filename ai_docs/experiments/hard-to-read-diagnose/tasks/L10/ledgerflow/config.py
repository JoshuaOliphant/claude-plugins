"""Configuration loading. Paths in a config file are relative to that file."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    pass


SOURCE_KINDS = ("csv", "jsonl", "feed")


@dataclass(frozen=True)
class SourceConfig:
    name: str
    kind: str
    path: Path | None = None
    feed: str | None = None
    since: date | None = None
    date_format: str = "%Y-%m-%d"
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetryConfig:
    attempts: int = 3
    backoff_seconds: float = 0.5
    multiplier: float = 2.0
    max_backoff_seconds: float = 30.0


@dataclass(frozen=True)
class ValidationConfig:
    enabled: bool = False
    sample_size: int = 25
    reject_zero_amounts: bool = True


@dataclass(frozen=True)
class Config:
    base_currency: str
    output: Path
    feeds_root: Path
    fx_rates: Path
    categories: Path
    sources: tuple[SourceConfig, ...]
    retry: RetryConfig = RetryConfig()
    validation: ValidationConfig = ValidationConfig()
    origin: Path | None = None

    def with_validation(self, enabled: bool) -> "Config":
        v = self.validation
        return _replace(self, validation=ValidationConfig(enabled, v.sample_size, v.reject_zero_amounts))

    def source(self, name: str) -> SourceConfig:
        for s in self.sources:
            if s.name == name:
                return s
        raise ConfigError(f"no source named {name!r}")


def _replace(cfg: Config, **changes: Any) -> Config:
    from dataclasses import replace

    return replace(cfg, **changes)


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA = PACKAGE_ROOT / "data"


def load_config(path: str | Path) -> Config:
    path = Path(path).resolve()
    try:
        with open(path, "rb") as fh:
            raw = tomllib.load(fh)
    except FileNotFoundError as exc:
        raise ConfigError(f"config not found: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: {exc}") from exc
    return parse_config(raw, base_dir=path.parent, origin=path)


def parse_config(raw: dict[str, Any], *, base_dir: Path, origin: Path | None = None) -> Config:
    ledger = raw.get("ledger", {})
    if "output" not in ledger:
        raise ConfigError("[ledger] output is required")
    base_currency = str(ledger.get("base_currency", "USD")).upper()

    def rel(value: str | None, default: Path | None = None) -> Path:
        if value is None:
            if default is None:
                raise ConfigError("missing path")
            return default
        p = Path(value).expanduser()
        return p if p.is_absolute() else (base_dir / p).resolve()

    data = raw.get("data", {})
    feeds = raw.get("feeds", {})
    retry_raw = raw.get("retry", {})
    val_raw = raw.get("validation", {})

    retry = RetryConfig(
        attempts=_positive_int(retry_raw.get("attempts", 3), "retry.attempts"),
        backoff_seconds=float(retry_raw.get("backoff_seconds", 0.5)),
        multiplier=float(retry_raw.get("multiplier", 2.0)),
        max_backoff_seconds=float(retry_raw.get("max_backoff_seconds", 30.0)),
    )
    validation = ValidationConfig(
        enabled=bool(val_raw.get("enabled", False)),
        sample_size=_positive_int(val_raw.get("sample_size", 25), "validation.sample_size"),
        reject_zero_amounts=bool(val_raw.get("reject_zero_amounts", True)),
    )

    sources = []
    seen: set[str] = set()
    for entry in raw.get("sources", []):
        src = _parse_source(entry, rel)
        if src.name in seen:
            raise ConfigError(f"duplicate source name {src.name!r}")
        seen.add(src.name)
        sources.append(src)
    if not sources:
        raise ConfigError("at least one [[sources]] entry is required")

    return Config(
        base_currency=base_currency,
        output=rel(ledger["output"]),
        feeds_root=rel(feeds.get("root"), PACKAGE_ROOT / "feeds"),
        fx_rates=rel(data.get("fx_rates"), DEFAULT_DATA / "fx_rates.csv"),
        categories=rel(data.get("categories"), DEFAULT_DATA / "categories.json"),
        sources=tuple(sources),
        retry=retry,
        validation=validation,
        origin=origin,
    )


def _parse_source(entry: dict[str, Any], rel) -> SourceConfig:
    try:
        name = str(entry["name"])
        kind = str(entry["kind"])
    except KeyError as exc:
        raise ConfigError(f"source is missing {exc.args[0]!r}") from exc
    if kind not in SOURCE_KINDS:
        raise ConfigError(f"source {name!r}: unknown kind {kind!r}")
    since = entry.get("since")
    if isinstance(since, str):
        since = date.fromisoformat(since)
    known = {"name", "kind", "path", "feed", "since", "date_format"}
    options = {k: v for k, v in entry.items() if k not in known}
    src = SourceConfig(
        name=name,
        kind=kind,
        path=rel(entry["path"]) if "path" in entry else None,
        feed=entry.get("feed"),
        since=since,
        date_format=entry.get("date_format", "%Y-%m-%d"),
        options=options,
    )
    if kind in ("csv", "jsonl") and src.path is None:
        raise ConfigError(f"source {name!r}: 'path' is required for {kind}")
    if kind == "feed" and not src.feed:
        raise ConfigError(f"source {name!r}: 'feed' is required for feed sources")
    return src


def _positive_int(value: Any, label: str) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{label} must be an integer") from exc
    if n < 1:
        raise ConfigError(f"{label} must be >= 1")
    return n
