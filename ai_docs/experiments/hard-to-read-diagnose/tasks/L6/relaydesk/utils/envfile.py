"""Minimal ``.env`` reader.

Supports the subset of the dotenv format we actually use::

    # comment
    KEY=value
    export KEY=value
    KEY="quoted value with # hash"
    KEY='single quoted'
    KEY=value  # trailing comment

Variable interpolation is deliberately not supported.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable, MutableMapping
from pathlib import Path

_LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")


class EnvFileError(ValueError):
    pass


def _unquote(raw: str, path: Path, lineno: int) -> str:
    if raw[:1] in {'"', "'"}:
        quote = raw[0]
        end = raw.find(quote, 1)
        if end == -1:
            raise EnvFileError(f"{path}:{lineno}: unterminated {quote} string")
        value = raw[1:end]
        if quote == '"':
            value = value.replace("\\n", "\n").replace('\\"', '"')
        return value
    hash_at = raw.find(" #")
    if hash_at != -1:
        raw = raw[:hash_at]
    return raw.strip()


def parse(text: str, path: Path | None = None) -> dict[str, str]:
    path = path or Path("<string>")
    values: dict[str, str] = {}
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _LINE.match(line)
        if not match:
            raise EnvFileError(f"{path}:{lineno}: cannot parse {line!r}")
        key, raw = match.groups()
        values[key] = _unquote(raw, path, lineno)
    return values


def read(path: Path) -> dict[str, str]:
    return parse(path.read_text(encoding="utf-8"), path)


def load(paths: Iterable[Path], environ: MutableMapping[str, str] | None = None) -> dict[str, str]:
    """Read each existing file in order (later files win) and copy the
    result into *environ* without replacing variables that are already set
    there.  Returns the keys that were applied."""
    environ = os.environ if environ is None else environ
    merged: dict[str, str] = {}
    for path in paths:
        if path.is_file():
            merged.update(read(path))
    applied: dict[str, str] = {}
    for key, value in merged.items():
        if key not in environ:
            environ[key] = value
            applied[key] = value
    return applied
