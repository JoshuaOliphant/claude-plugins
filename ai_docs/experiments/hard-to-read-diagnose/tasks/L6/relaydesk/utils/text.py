"""Small string helpers used by the formatter and the CLI tables."""

from __future__ import annotations

import re
import unicodedata

_WS = re.compile(r"\s+")


def squash(text: str) -> str:
    return _WS.sub(" ", text).strip()


def truncate(text: str, limit: int, ellipsis: str = "…") -> str:
    text = squash(text)
    if len(text) <= limit:
        return text
    cut = text[: max(limit - len(ellipsis), 0)].rstrip()
    space = cut.rfind(" ")
    if space > limit // 2:
        cut = cut[:space]
    return cut + ellipsis


def slugify(text: str) -> str:
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    norm = re.sub(r"[^a-zA-Z0-9]+", "-", norm).strip("-").lower()
    return norm or "x"


def table(rows: list[list[str]], headers: list[str]) -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    def fmt(cells: list[str]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells)).rstrip()
    lines = [fmt(headers), fmt(["-" * w for w in widths])]
    lines.extend(fmt(row) for row in rows)
    return "\n".join(lines)
