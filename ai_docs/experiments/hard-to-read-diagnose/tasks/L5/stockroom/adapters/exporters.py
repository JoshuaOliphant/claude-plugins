"""Render a :class:`~stockroom.services.reports.Report` in one of several formats."""

from __future__ import annotations

from pathlib import Path

from stockroom.services.reports import Report
from stockroom.utils import dates
from stockroom.utils.formatting import render_csv, render_json, render_table

FORMATS = ("table", "csv", "json")


def render(report: Report, fmt: str = "table") -> str:
    fmt = fmt.lower()
    if fmt == "table":
        return _table(report)
    if fmt == "csv":
        return render_csv(report.columns, report.rows)
    if fmt == "json":
        return render_json(
            report.columns,
            report.rows,
            report=report.name,
            as_of=report.as_of.isoformat() if report.as_of else None,
            totals=report.totals,
        )
    raise ValueError(f"unknown format {fmt!r}; choose from {', '.join(FORMATS)}")


def _table(report: Report) -> str:
    header = report.title
    if report.as_of:
        header += f" (as of {report.as_of.isoformat()})"
    lines = [header, "=" * len(header), ""]
    if report.rows:
        lines.append(render_table(report.columns, report.rows))
    else:
        lines.append("(no rows)")
    if report.totals:
        lines.append("")
        lines.append("  ".join(f"{k}: {v}" for k, v in report.totals.items() if not k.endswith("_cents")))
    return "\n".join(lines)


def write(report: Report, path: Path, fmt: str | None = None) -> Path:
    """Write a report to ``path``; the format defaults to the file extension."""
    fmt = fmt or {".csv": "csv", ".json": "json"}.get(path.suffix.lower(), "table")
    text = render(report, fmt)
    if fmt == "table":
        text = f"# generated {dates.timestamp()}\n{text}\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
