"""Iterator helpers."""

from __future__ import annotations

from itertools import chain, islice
from typing import Iterable, Iterator, TypeVar

T = TypeVar("T")

_MISSING = object()


def peek(iterable: Iterable[T]) -> tuple[T | None, Iterator[T]]:
    """Return the first item and an iterator that still yields every item."""
    it = iter(iterable)
    first = next(it, _MISSING)
    if first is _MISSING:
        return None, iter(())
    return first, chain([first], it)


def chunked(iterable: Iterable[T], size: int) -> Iterator[list[T]]:
    if size < 1:
        raise ValueError("size must be >= 1")
    it = iter(iterable)
    while batch := list(islice(it, size)):
        yield batch
