"""A name/alias/extension registry for pluggable components."""

from __future__ import annotations

import logging
from typing import Generic, Iterator, TypeVar

log = logging.getLogger(__name__)

T = TypeVar("T")


class RegistryError(Exception):
    pass


class UnknownPluginError(RegistryError, LookupError):
    def __init__(self, kind: str, key: str, known: list[str]):
        self.kind = kind
        self.key = key
        self.known = known
        hint = ", ".join(known) if known else "none registered"
        super().__init__(f"unknown {kind} {key!r} (available: {hint})")


def _norm_name(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def _norm_ext(ext: str) -> str:
    ext = ext.strip().lower()
    if ext and not ext.startswith("."):
        ext = "." + ext
    return ext


class Registry(Generic[T]):
    """Maps canonical names, aliases and file extensions to plugins."""

    def __init__(self, kind: str):
        self.kind = kind
        self._by_name: dict[str, T] = {}
        self._aliases: dict[str, str] = {}
        self._extensions: dict[str, str] = {}

    def register(self, name: str, plugin: T, *, aliases=(), extensions=()) -> T:
        key = _norm_name(name)
        existing = self._by_name.get(key)
        if existing is not None and existing is not plugin:
            raise RegistryError(f"{self.kind} {key!r} is already registered by {existing!r}")
        self._by_name[key] = plugin
        for alias in aliases:
            alias_key = _norm_name(alias)
            owner = self._aliases.get(alias_key)
            if alias_key in self._by_name and alias_key != key:
                raise RegistryError(f"alias {alias!r} shadows the {self.kind} of the same name")
            if owner is not None and owner != key:
                raise RegistryError(f"alias {alias!r} is already used by {self.kind} {owner!r}")
            self._aliases[alias_key] = key
        for ext in extensions:
            ext_key = _norm_ext(ext)
            previous = self._extensions.get(ext_key)
            if previous is not None and previous != key:
                log.debug("%s for %s: %r -> %r", self.kind, ext_key, previous, key)
            self._extensions[ext_key] = key
        return plugin

    def canonical(self, name: str) -> str:
        key = _norm_name(name)
        if key in self._by_name:
            return key
        if key in self._aliases:
            return self._aliases[key]
        raise UnknownPluginError(self.kind, name, self.names())

    def get(self, name: str) -> T:
        return self._by_name[self.canonical(name)]

    def name_for_extension(self, ext: str) -> str:
        ext_key = _norm_ext(ext)
        try:
            return self._extensions[ext_key]
        except KeyError:
            raise UnknownPluginError(f"{self.kind} for extension", ext_key, sorted(self._extensions)) from None

    def for_extension(self, ext: str) -> T:
        return self._by_name[self.name_for_extension(ext)]

    def names(self) -> list[str]:
        return sorted(self._by_name)

    def aliases_of(self, name: str) -> list[str]:
        key = self.canonical(name)
        return sorted(a for a, owner in self._aliases.items() if owner == key)

    def extensions_of(self, name: str) -> list[str]:
        key = self.canonical(name)
        return sorted(e for e, owner in self._extensions.items() if owner == key)

    def __contains__(self, name: str) -> bool:
        try:
            self.canonical(name)
        except UnknownPluginError:
            return False
        return True

    def __iter__(self) -> Iterator[tuple[str, T]]:
        for key in self.names():
            yield key, self._by_name[key]

    def __len__(self) -> int:
        return len(self._by_name)

    def clear(self) -> None:
        self._by_name.clear()
        self._aliases.clear()
        self._extensions.clear()
