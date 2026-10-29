"""Postcode normalisation for the countries freightdesk ships to."""

from __future__ import annotations

import re
from functools import lru_cache

PATTERNS = {
    "DE": re.compile(r"^\d{5}$"),
    "AT": re.compile(r"^\d{4}$"),
    "CH": re.compile(r"^\d{4}$"),
    "FR": re.compile(r"^\d{5}$"),
    "NL": re.compile(r"^\d{4}[A-Z]{2}$"),
}

PREFIXES = ("D-", "A-", "CH-", "F-", "NL-")


class PostcodeError(ValueError):
    pass


@lru_cache(maxsize=4096)
def normalize_postcode(country: str, raw: str) -> str:
    """Return the canonical postcode for ``country`` or raise PostcodeError."""
    country = country.upper()
    text = raw.strip().upper()
    for prefix in PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    text = text.replace(" ", "")
    pattern = PATTERNS.get(country)
    if pattern is None:
        raise PostcodeError(f"unsupported country {country!r}")
    if not pattern.match(text):
        raise PostcodeError(f"invalid {country} postcode {raw!r}")
    if country == "NL":
        return f"{text[:4]} {text[4:]}"
    return text


def region_digit(country: str, postcode: str) -> int:
    """Leading routing digit of a normalised postcode."""
    return int(normalize_postcode(country, postcode)[0])
