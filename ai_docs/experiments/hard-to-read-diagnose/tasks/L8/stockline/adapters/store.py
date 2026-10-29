"""Namespaced key/value storage.

Records are JSON-compatible dicts grouped into namespaces (``products``,
``suppliers``, ``journal``, ``runs``, ``meta``).  ``MemoryStore`` keeps
everything in process; ``JsonFileStore`` adds load/save against a single
JSON document so the CLI can persist the catalog between runs.

Callers always receive copies, so mutating a returned record never changes
stored state behind the store's back.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Iterator

from stockline.domain.errors import StoreFormatError

FORMAT_VERSION = 3


class MemoryStore:
    def __init__(self) -> None:
        self._data: dict[str, dict[str, dict]] = {}
        self._revision = 0

    @property
    def revision(self) -> int:
        """Counter bumped by every write.

        Readers that keep derived data (indexes, summaries) compare it with
        the value they saw last time to know whether a refresh is needed.
        """
        return self._revision

    def namespaces(self) -> list[str]:
        return sorted(self._data)

    def get(self, namespace: str, key: str) -> dict | None:
        rec = self._data.get(namespace, {}).get(key)
        return dict(rec) if rec is not None else None

    def put(self, namespace: str, key: str, record: dict) -> None:
        self._data.setdefault(namespace, {})[key] = dict(record)
        self._touch()

    def delete(self, namespace: str, key: str) -> bool:
        bucket = self._data.get(namespace)
        if not bucket or key not in bucket:
            return False
        del bucket[key]
        self._touch()
        return True

    def scan(self, namespace: str) -> Iterator[tuple[str, dict]]:
        for key, rec in list(self._data.get(namespace, {}).items()):
            yield key, dict(rec)

    def keys(self, namespace: str) -> list[str]:
        return list(self._data.get(namespace, {}))

    def count(self, namespace: str) -> int:
        return len(self._data.get(namespace, {}))

    def _touch(self) -> None:
        self._revision += 1

    def snapshot(self) -> dict:
        return {
            "format": FORMAT_VERSION,
            "namespaces": {ns: dict(bucket) for ns, bucket in self._data.items()},
        }


class JsonFileStore(MemoryStore):
    """MemoryStore persisted to one JSON file, written atomically on save()."""

    def __init__(self, path: str | os.PathLike):
        super().__init__()
        self.path = Path(path)
        self._dirty = False
        if self.path.exists():
            self._load()

    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise StoreFormatError(f"{self.path}: corrupt store file ({exc})") from exc
        version = raw.get("format")
        if version != FORMAT_VERSION:
            raise StoreFormatError(
                f"{self.path}: store format {version!r}, expected {FORMAT_VERSION}"
            )
        self._data = {ns: dict(bucket) for ns, bucket in raw.get("namespaces", {}).items()}

    def _touch(self) -> None:
        super()._touch()
        self._dirty = True

    @property
    def dirty(self) -> bool:
        return self._dirty

    def save(self) -> None:
        if not self._dirty:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".stockline-", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self.snapshot(), fh, indent=1, sort_keys=True)
                fh.write("\n")
            os.replace(tmp, self.path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
        self._dirty = False

    def __enter__(self) -> "JsonFileStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is None:
            self.save()
