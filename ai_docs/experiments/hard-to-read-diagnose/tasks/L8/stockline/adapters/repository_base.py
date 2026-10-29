"""Shared machinery for repositories that need secondary indexes.

A repository owns one store namespace.  Each declared index maps a key
derived from a record (``sku``, ``supplier:part`` ...) to the record's
primary key.  Indexes are built lazily from a scan of the namespace and
then kept up to date by the repository's own writes; if the store has
changed in some other way since the index was built, it is rebuilt on the
next lookup.
"""

from __future__ import annotations

from typing import Callable, Iterator

from stockline.adapters.store import MemoryStore

IndexKeyFn = Callable[[dict], "str | None"]


class IndexedRepository:
    namespace: str = ""
    indexes: dict[str, IndexKeyFn] = {}

    def __init__(self, store: MemoryStore):
        if not self.namespace:
            raise TypeError(f"{type(self).__name__} must set a namespace")
        self._store = store
        self._index_data: dict[str, dict[str, str]] = {}
        self._indexed_revision: int | None = None

    # -- index maintenance -------------------------------------------------

    def _ensure_indexes(self) -> None:
        if self._indexed_revision == self._store.revision:
            return
        built: dict[str, dict[str, str]] = {name: {} for name in self.indexes}
        for key, rec in self._store.scan(self.namespace):
            for name, fn in self.indexes.items():
                value = fn(rec)
                if value:
                    built[name][value] = key
        self._index_data = built
        self._indexed_revision = self._store.revision

    def _lookup(self, index: str, value: str) -> dict | None:
        self._ensure_indexes()
        key = self._index_data[index].get(value)
        if key is None:
            return None
        return self._store.get(self.namespace, key)

    def _put(self, key: str, record: dict) -> None:
        self._ensure_indexes()
        previous = self._store.get(self.namespace, key)
        self._store.put(self.namespace, key, record)
        for name, fn in self.indexes.items():
            bucket = self._index_data[name]
            if previous is not None:
                old = fn(previous)
                if old and bucket.get(old) == key:
                    del bucket[old]
            new = fn(record)
            if new:
                bucket[new] = key
        self._indexed_revision = self._store.revision

    def _remove(self, key: str) -> bool:
        self._ensure_indexes()
        previous = self._store.get(self.namespace, key)
        if previous is None:
            return False
        self._store.delete(self.namespace, key)
        for name, fn in self.indexes.items():
            old = fn(previous)
            if old and self._index_data[name].get(old) == key:
                del self._index_data[name][old]
        self._indexed_revision = self._store.revision
        return True

    # -- plain access ------------------------------------------------------

    def _get(self, key: str) -> dict | None:
        return self._store.get(self.namespace, key)

    def _scan(self) -> Iterator[tuple[str, dict]]:
        return self._store.scan(self.namespace)

    def __len__(self) -> int:
        return self._store.count(self.namespace)
