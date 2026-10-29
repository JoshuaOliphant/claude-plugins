"""Formatting helpers for plain-text receipts and summaries."""

from __future__ import annotations

from collections.abc import Iterable

DEFAULT_WIDTH = 64


def money(cents: int, currency: str = "USD") -> str:
    """Format integer cents, e.g. ``-1234`` -> ``-$12.34``."""
    symbol = {"USD": "$", "CAD": "CA$", "EUR": "€"}.get(currency, currency + " ")
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents), 100)
    return f"{sign}{symbol}{whole:,}.{frac:02d}"


def truncate(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    if width <= 1:
        return text[:width]
    return text[: width - 1] + "…"


def two_column(left: str, right: str, width: int = DEFAULT_WIDTH) -> str:
    """Left-align ``left`` and right-align ``right`` within ``width``."""
    room = width - len(right) - 1
    left = truncate(left, max(room, 1))
    return left + " " * max(width - len(left) - len(right), 1) + right


def rule(char: str = "-", width: int = DEFAULT_WIDTH) -> str:
    return char * width


def bullet_list(items: Iterable[str], indent: int = 2, marker: str = "-") -> list[str]:
    pad = " " * indent
    return [f"{pad}{marker} {item}" for item in items]


def pluralize(count: int, singular: str, plural: str | None = None) -> str:
    word = singular if count == 1 else (plural or singular + "s")
    return f"{count} {word}"


def title_case(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.replace("_", " ").replace("-", " ").split())
