"""Plain-text and JSON rendering for report output."""

from __future__ import annotations

import json
from typing import Any, Iterable, Sequence


def render_table(headers: Sequence[str], rows: Iterable[Sequence[Any]],
                 align: Sequence[str] | None = None) -> str:
    """Render rows as a fixed-width table.

    ``align`` holds one of ``"<"`` or ``">"`` per column; numbers default to
    right alignment, everything else to left.
    """
    materialised = [[_cell(value) for value in row] for row in rows]
    widths = [len(header) for header in headers]
    for row in materialised:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    if align is None:
        align = ["<"] * len(headers)
    lines = [
        "  ".join(f"{header:{align[i]}{widths[i]}}" for i, header in enumerate(headers)),
        "  ".join("-" * width for width in widths),
    ]
    for row in materialised:
        lines.append("  ".join(f"{cell:{align[i]}{widths[i]}}" for i, cell in enumerate(row)))
    return "\n".join(lines)


def _cell(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)


def to_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, default=_json_default)


def _json_default(value: Any) -> Any:
    if hasattr(value, "to_json"):
        return value.to_json()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(f"cannot serialise {type(value).__name__}")


def plural(count: int, noun: str, suffix: str = "s") -> str:
    return f"{count} {noun}{'' if count == 1 else suffix}"
