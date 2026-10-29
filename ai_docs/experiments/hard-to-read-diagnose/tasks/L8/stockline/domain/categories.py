"""Category tree loaded from ``data/categories.json``.

Category codes are dotted paths (``hardware.fasteners.screws``).  The tree
is small (a few hundred nodes) and loaded once per process.
"""

from __future__ import annotations

import json
from pathlib import Path


class CategoryTree:
    def __init__(self, nodes: dict[str, dict]):
        self._nodes = nodes

    @classmethod
    def from_file(cls, path: Path) -> "CategoryTree":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        nodes = {}
        for item in raw["categories"]:
            nodes[item["code"]] = {"name": item["name"], "parent": item.get("parent")}
        tree = cls(nodes)
        tree._check()
        return tree

    def _check(self) -> None:
        for code, node in self._nodes.items():
            parent = node["parent"]
            if parent is not None and parent not in self._nodes:
                raise ValueError(f"category {code!r} has unknown parent {parent!r}")

    def __contains__(self, code: str) -> bool:
        return code in self._nodes

    def __len__(self) -> int:
        return len(self._nodes)

    def name(self, code: str) -> str:
        return self._nodes[code]["name"]

    def lineage(self, code: str) -> list[str]:
        """Codes from *code* up to the root, most specific first."""
        out = []
        seen = set()
        while code is not None and code in self._nodes and code not in seen:
            out.append(code)
            seen.add(code)
            code = self._nodes[code]["parent"]
        return out

    def label(self, code: str) -> str:
        return " > ".join(self.name(c) for c in reversed(self.lineage(code)))

    def children(self, code: str | None) -> list[str]:
        return sorted(c for c, n in self._nodes.items() if n["parent"] == code)

    def resolve(self, code: str) -> str | None:
        """Return the deepest known ancestor-or-self of *code*.

        Suppliers sometimes send categories one level deeper than ours.
        """
        parts = code.split(".")
        while parts:
            candidate = ".".join(parts)
            if candidate in self._nodes:
                return candidate
            parts.pop()
        return None
