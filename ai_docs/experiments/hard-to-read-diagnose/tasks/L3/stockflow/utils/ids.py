"""Identifier generation for movements and runs."""

from __future__ import annotations

import hashlib
import itertools

_sequence = itertools.count(1)


def next_sequence() -> int:
    return next(_sequence)


def movement_id(warehouse: str, reference: str, sku: str) -> str:
    """Stable id derived from the movement's natural key."""
    digest = hashlib.sha1(f"{warehouse}|{reference}|{sku}".encode()).hexdigest()
    return f"MV-{digest[:12].upper()}"


def run_id(prefix: str = "RUN") -> str:
    return f"{prefix}-{next_sequence():06d}"
