"""Plain-text table rendering."""

from __future__ import annotations

from typing import Iterable, Sequence


def format_int(value: int) -> str:
    return f"{value:,}"


def format_table(headers: Sequence[str], rows: Iterable[Sequence[object]],
                 align: Sequence[str] | None = None) -> str:
    """Render rows as a fixed-width table. ``align`` holds 'l' or 'r' per column."""
    cells = [[str(h) for h in headers]]
    for row in rows:
        cells.append(["" if v is None else str(v) for v in row])
    ncols = len(headers)
    align = list(align or ["l"] * ncols)
    widths = [max(len(r[i]) for r in cells) for i in range(ncols)]

    def render(row: list[str]) -> str:
        parts = []
        for i, value in enumerate(row):
            if align[i] == "r":
                parts.append(value.rjust(widths[i]))
            else:
                parts.append(value.ljust(widths[i]))
        return "  ".join(parts).rstrip()

    lines = [render(cells[0]), "  ".join("-" * w for w in widths)]
    lines.extend(render(r) for r in cells[1:])
    return "\n".join(lines)


def banner(title: str, width: int = 60) -> str:
    return f"{title}\n{'=' * min(width, max(len(title), 8))}"
