"""Plain-text rendering of tabular data."""

from __future__ import annotations

import csv
import io
import json
from typing import Any, Iterable, Sequence


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def _is_numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def truncate(text: str, width: int) -> str:
    if width < 4 or len(text) <= width:
        return text
    return text[: width - 1] + "…"


def render_table(
    headers: Sequence[str],
    rows: Iterable[Sequence[Any]],
    *,
    max_width: int = 32,
) -> str:
    rows = [list(r) for r in rows]
    text_rows = [[truncate(_cell(v), max_width) for v in r] for r in rows]
    widths = [len(h) for h in headers]
    for r in text_rows:
        for i, v in enumerate(r):
            widths[i] = max(widths[i], len(v))

    numeric = [
        bool(rows) and all(_is_numeric(r[i]) or r[i] is None for r in rows)
        for i in range(len(headers))
    ]

    def fmt(values: Sequence[str]) -> str:
        parts = []
        for i, v in enumerate(values):
            parts.append(v.rjust(widths[i]) if numeric[i] else v.ljust(widths[i]))
        return "  ".join(parts).rstrip()

    out = [fmt(list(headers)), "  ".join("-" * w for w in widths)]
    out.extend(fmt(r) for r in text_rows)
    return "\n".join(out)


def render_csv(headers: Sequence[str], rows: Iterable[Sequence[Any]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(headers)
    for r in rows:
        writer.writerow([_cell(v) for v in r])
    return buf.getvalue()


def render_json(headers: Sequence[str], rows: Iterable[Sequence[Any]], **meta: Any) -> str:
    keys = [h.lower().replace(" ", "_") for h in headers]
    records = [dict(zip(keys, r)) for r in rows]
    payload: dict[str, Any] = dict(meta)
    payload["rows"] = records
    return json.dumps(payload, indent=2, default=str)
