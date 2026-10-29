"""Apply the reference fix: track store revisions per namespace so that writes
to unrelated namespaces (journal, runs, meta sequences) no longer invalidate a
repository's secondary indexes and force a full rescan on every row."""

import sys
from pathlib import Path


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, f"expected exactly one match in {path}: {old!r}"
    path.write_text(text.replace(old, new), encoding="utf-8")


def main(tree: str) -> None:
    root = Path(tree)
    store = root / "stockline" / "adapters" / "store.py"
    base = root / "stockline" / "adapters" / "repository_base.py"

    replace(store, """        self._data: dict[str, dict[str, dict]] = {}
        self._revision = 0
""", """        self._data: dict[str, dict[str, dict]] = {}
        self._revision = 0
        self._ns_revisions: dict[str, int] = {}
""")
    replace(store, """    def namespaces(self) -> list[str]:""", """    def namespace_revision(self, namespace: str) -> int:
        return self._ns_revisions.get(namespace, 0)

    def namespaces(self) -> list[str]:""")
    replace(store, """        self._data.setdefault(namespace, {})[key] = dict(record)
        self._touch()
""", """        self._data.setdefault(namespace, {})[key] = dict(record)
        self._ns_revisions[namespace] = self._ns_revisions.get(namespace, 0) + 1
        self._touch()
""")
    replace(store, """        del bucket[key]
        self._touch()
""", """        del bucket[key]
        self._ns_revisions[namespace] = self._ns_revisions.get(namespace, 0) + 1
        self._touch()
""")
    replace(store, """        self._data = {ns: dict(bucket) for ns, bucket in raw.get("namespaces", {}).items()}
""", """        self._data = {ns: dict(bucket) for ns, bucket in raw.get("namespaces", {}).items()}
        self._ns_revisions = {}
""")

    text = base.read_text(encoding="utf-8")
    old = "self._store.revision"
    assert text.count(old) == 4, text.count(old)
    base.write_text(text.replace(old, "self._store.namespace_revision(self.namespace)"), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
