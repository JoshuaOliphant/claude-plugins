"""Text normalisation used when mapping supplier data onto the catalog."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from functools import lru_cache

_WS = re.compile(r"\s+")
_SKU_JUNK = re.compile(r"[^A-Z0-9\-_/]")
_SMALL_WORDS = {"a", "an", "and", "for", "in", "of", "on", "or", "the", "to", "with", "x"}
_KEEP_UPPER = re.compile(r"^(?:[A-Z]{2,4}|\d+[A-Z]+|[A-Z]+\d+[A-Z0-9]*)$")


def collapse_ws(text: str) -> str:
    return _WS.sub(" ", text or "").strip()


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def clean_sku(value: str) -> str:
    text = strip_accents(str(value or "")).upper().replace(" ", "")
    return _SKU_JUNK.sub("", text)


@lru_cache(maxsize=65536)
def display_name(value: str) -> str:
    """Title-case a product name while keeping codes like ``M8`` or ``PVC``."""
    words = collapse_ws(value).split(" ")
    out = []
    for i, word in enumerate(words):
        if not word:
            continue
        if _KEEP_UPPER.match(word):
            out.append(word)
        elif i > 0 and word.lower() in _SMALL_WORDS:
            out.append(word.lower())
        else:
            out.append(word[:1].upper() + word[1:].lower())
    return " ".join(out)


def match_key(value: str) -> str:
    """Loose key for fuzzy comparisons: lowercase alphanumerics only."""
    return re.sub(r"[^a-z0-9]+", "", strip_accents(value).lower())


def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, match_key(a), match_key(b)).ratio()


def truncate(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    return text[: max(width - 1, 0)] + "…"
