"""Turn raw values (TOML scalars, environment strings, CLI strings) into the
types declared in :mod:`relaydesk.settings.schema`."""

from __future__ import annotations

import re
from pathlib import Path

from .schema import Setting


class SettingError(ValueError):
    """Raised when a value cannot be coerced to its declared kind."""


_TRUE = {"1", "true", "yes", "on", "y", "t"}
_FALSE = {"0", "false", "no", "off", "n", "f", ""}

_DURATION = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(ms|s|m|h)?\s*$")
_UNIT = {"ms": 0.001, "s": 1.0, "m": 60.0, "h": 3600.0, None: 1.0}


def parse_bool(raw: object) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return raw != 0
    text = str(raw).strip().lower()
    if text in _TRUE:
        return True
    if text in _FALSE:
        return False
    raise SettingError(f"not a boolean: {raw!r}")


def parse_int(raw: object) -> int:
    if isinstance(raw, bool):
        raise SettingError(f"not an integer: {raw!r}")
    if isinstance(raw, int):
        return raw
    text = str(raw).strip().replace("_", "")
    try:
        return int(text, 10)
    except ValueError:
        raise SettingError(f"not an integer: {raw!r}") from None


def parse_float(raw: object) -> float:
    try:
        return float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise SettingError(f"not a number: {raw!r}") from None


def parse_duration(raw: object) -> float:
    """Return seconds.  Accepts numbers (seconds) or strings like ``1.5s``,
    ``250ms``, ``2m``."""
    if isinstance(raw, bool):
        raise SettingError(f"not a duration: {raw!r}")
    if isinstance(raw, (int, float)):
        return float(raw)
    match = _DURATION.match(str(raw))
    if not match:
        raise SettingError(f"not a duration: {raw!r}")
    value, unit = match.groups()
    return float(value) * _UNIT[unit]


def parse_list(raw: object) -> list[str]:
    if isinstance(raw, (list, tuple)):
        return [str(item) for item in raw]
    return [part.strip() for part in str(raw).split(",") if part.strip()]


def parse_str(raw: object) -> str:
    return str(raw).strip()


def parse_path(raw: object) -> Path:
    return Path(str(raw).strip()).expanduser()


_PARSERS = {
    "bool": parse_bool,
    "int": parse_int,
    "float": parse_float,
    "duration": parse_duration,
    "list": parse_list,
    "str": parse_str,
    "path": parse_path,
}


def coerce(setting: Setting, raw: object) -> object:
    try:
        parser = _PARSERS[setting.kind]
    except KeyError:
        raise SettingError(f"{setting.key}: unknown kind {setting.kind!r}") from None
    try:
        value = parser(raw)
    except SettingError as exc:
        raise SettingError(f"{setting.key}: {exc}") from None
    if setting.minimum is not None and isinstance(value, (int, float)):
        if value < setting.minimum:
            raise SettingError(
                f"{setting.key}: {value!r} is below the minimum {setting.minimum!r}"
            )
    if setting.choices and isinstance(value, str):
        value = value.lower()
        if value not in setting.choices:
            raise SettingError(
                f"{setting.key}: {value!r} is not one of {', '.join(setting.choices)}"
            )
    return value
