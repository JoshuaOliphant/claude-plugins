"""Memoisation helpers for pure lookups."""

from __future__ import annotations

import functools
from typing import Callable, Hashable, TypeVar

T = TypeVar("T")

_MISSING = object()


def memoize_method(func: Callable[..., T]) -> Callable[..., T]:
    """Cache a method's result per instance, keyed by its positional args.

    Intended for pure computations on immutable state; a value may be
    computed more than once if two callers ask at the same moment, which is
    harmless because the result is always the same.
    """
    attr = f"_memo_{func.__name__}"

    @functools.wraps(func)
    def wrapper(self, *args: Hashable) -> T:
        cache = self.__dict__.get(attr)
        if cache is None:
            cache = {}
            self.__dict__[attr] = cache
        value = cache.get(args, _MISSING)
        if value is _MISSING:
            value = func(self, *args)
            cache[args] = value
        return value

    def clear(self) -> None:
        self.__dict__.pop(attr, None)

    wrapper.clear = clear  # type: ignore[attr-defined]
    return wrapper


class LazyValue:
    """Compute a value on first access and keep it."""

    __slots__ = ("_factory", "_value")

    def __init__(self, factory: Callable[[], T]) -> None:
        self._factory = factory
        self._value = _MISSING

    @property
    def loaded(self) -> bool:
        return self._value is not _MISSING

    def get(self):
        if self._value is _MISSING:
            self._value = self._factory()
        return self._value

    def reset(self) -> None:
        self._value = _MISSING
