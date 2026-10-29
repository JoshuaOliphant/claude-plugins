"""Locating input files and resolving configured paths."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PACKAGE_ROOT.parent

MOVEMENT_SUFFIXES = (".csv", ".tsv", ".txt")


def resolve(base: Path, value: str) -> Path:
    p = Path(value).expanduser()
    if not p.is_absolute():
        p = base / p
    return p.resolve()


def discover_movement_files(inputs: Iterable[str | Path], pattern: str = "*") -> list[Path]:
    """Expand directories into movement files; keep explicit files as given.

    The result is de-duplicated and sorted so runs are reproducible.
    """
    found: set[Path] = set()
    for item in inputs:
        path = Path(item)
        if path.is_dir():
            for child in path.glob(pattern):
                if child.is_file() and child.suffix.lower() in MOVEMENT_SUFFIXES:
                    found.add(child.resolve())
        elif path.is_file():
            found.add(path.resolve())
        else:
            raise FileNotFoundError(f"input not found: {item}")
    return sorted(found)
