"""Input validation primitives used by the inbound adapters."""

from __future__ import annotations

import re
from dataclasses import MISSING, fields, is_dataclass
from datetime import date
from typing import Any, TypeVar

T = TypeVar("T")

_SKU_RE = re.compile(r"^[A-Z0-9]+(?:-[A-Z0-9]+)*$")
_CUSTOMER_RE = re.compile(r"^C-\d{4}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ValidationError(ValueError):
    """Raised when an inbound payload cannot be accepted."""

    def __init__(self, message: str, *, field: str | None = None):
        super().__init__(message)
        self.field = field

    def to_dict(self) -> dict[str, Any]:
        return {"error": "validation", "message": str(self), "field": self.field}


def require(condition: bool, message: str, *, field: str | None = None) -> None:
    if not condition:
        raise ValidationError(message, field=field)


def require_type(value: Any, expected: type | tuple[type, ...], field: str) -> Any:
    if isinstance(value, bool) and expected in (int, (int,)):
        raise ValidationError(f"{field} must be an integer", field=field)
    if not isinstance(value, expected):
        name = getattr(expected, "__name__", None) or "/".join(t.__name__ for t in expected)
        raise ValidationError(f"{field} must be of type {name}", field=field)
    return value


def require_sku(value: Any, field: str = "sku") -> str:
    require_type(value, str, field)
    require(bool(_SKU_RE.match(value)), f"{field} {value!r} is not a valid SKU", field=field)
    return value


def require_customer_id(value: Any, field: str = "customer_id") -> str:
    require_type(value, str, field)
    require(bool(_CUSTOMER_RE.match(value)), f"{field} {value!r} is not a valid customer id", field=field)
    return value


def optional_email(value: Any, field: str = "email") -> str | None:
    if value is None:
        return None
    require_type(value, str, field)
    require(bool(_EMAIL_RE.match(value)), f"{field} {value!r} is not a valid email", field=field)
    return value


def require_positive_int(value: Any, field: str, *, maximum: int | None = None) -> int:
    require_type(value, int, field)
    require(value > 0, f"{field} must be positive", field=field)
    if maximum is not None:
        require(value <= maximum, f"{field} must be at most {maximum}", field=field)
    return value


def optional_date(value: Any, field: str) -> date | None:
    if value is None:
        return None
    require_type(value, str, field)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"{field} must be an ISO date (YYYY-MM-DD)", field=field) from exc


def build_dataclass(cls: type[T], data: dict[str, Any], *, context: str) -> T:
    """Instantiate dataclass ``cls`` from ``data``.

    Unknown keys are rejected so that typos in client payloads surface as
    errors instead of being silently ignored.  Required fields (those without
    a default) must be present.
    """
    if not is_dataclass(cls):
        raise TypeError(f"{cls!r} is not a dataclass")
    require_type(data, dict, context)
    known = {f.name: f for f in fields(cls) if f.init}
    unknown = sorted(set(data) - set(known))
    require(not unknown, f"{context}: unknown field(s) {', '.join(unknown)}", field=context)
    kwargs: dict[str, Any] = {}
    for name, spec in known.items():
        if name in data:
            kwargs[name] = data[name]
        elif spec.default is MISSING and spec.default_factory is MISSING:
            raise ValidationError(f"{context}: missing required field '{name}'", field=f"{context}.{name}")
    try:
        return cls(**kwargs)
    except (TypeError, ValueError) as exc:
        if isinstance(exc, ValidationError):
            raise
        raise ValidationError(f"{context}: {exc}", field=context) from exc
