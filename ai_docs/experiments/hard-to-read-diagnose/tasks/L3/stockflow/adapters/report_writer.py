"""Render reports as text, JSON or CSV."""

from __future__ import annotations

import csv
import io
import json
from typing import Optional

from stockflow.domain.models import IngestResult
from stockflow.services.reporting import StockReport
from stockflow.utils.textfmt import banner, format_int, format_table
from stockflow.utils.timeutil import iso

FORMATS = ("text", "json", "csv")


def _ingest_dict(totals: IngestResult) -> dict:
    return {
        "rows_read": totals.rows_read,
        "posted": totals.posted,
        "rejected": totals.rejected,
        "duplicates": totals.duplicates,
    }


def render_json(report: StockReport, ingest: Optional[IngestResult] = None,
                files: Optional[list[IngestResult]] = None) -> str:
    payload = {
        "as_of": iso(report.as_of),
        "totals": {
            "on_hand": report.total_on_hand,
            "movements": report.movement_count,
            "lines": len(report.rows),
            "by_warehouse": report.by_warehouse(),
            "by_category": report.by_category(),
        },
        "levels": [
            {
                "warehouse": r.warehouse,
                "sku": r.sku,
                "on_hand": r.on_hand,
                "received": r.received,
                "issued": r.issued,
                "movements": r.movements,
                "last_movement": iso(r.last_movement),
                "status": r.status,
            }
            for r in report.rows
        ],
    }
    if ingest is not None:
        payload["ingest"] = _ingest_dict(ingest)
    if files is not None:
        payload["files"] = [dict(source=f.source, **_ingest_dict(f)) for f in files]
    return json.dumps(payload, indent=2, sort_keys=False)


def render_csv(report: StockReport, ingest: Optional[IngestResult] = None,
               files: Optional[list[IngestResult]] = None) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["warehouse", "sku", "description", "on_hand", "received",
                     "issued", "movements", "last_movement", "status"])
    for r in report.rows:
        writer.writerow([r.warehouse, r.sku, r.description, r.on_hand, r.received,
                         r.issued, r.movements, iso(r.last_movement), r.status])
    return buf.getvalue()


def render_text(report: StockReport, ingest: Optional[IngestResult] = None,
                files: Optional[list[IngestResult]] = None) -> str:
    out = [banner(f"Stock on hand as of {iso(report.as_of) or 'n/a'}")]
    if ingest is not None:
        out.append(
            f"rows read {format_int(ingest.rows_read)}, posted {format_int(ingest.posted)}, "
            f"rejected {format_int(ingest.rejected)}, duplicates {format_int(ingest.duplicates)}"
        )
    out.append("")
    out.append(
        format_table(
            ["WH", "SKU", "Description", "On hand", "Moves", "Last", "Status"],
            [
                (r.warehouse, r.sku, r.description[:28], format_int(r.on_hand),
                 r.movements, iso(r.last_movement), r.status)
                for r in report.rows
            ],
            align=["l", "l", "l", "r", "r", "l", "l"],
        )
    )
    out.append("")
    out.append(
        format_table(
            ["Warehouse", "On hand"],
            [(wh, format_int(v)) for wh, v in report.by_warehouse().items()],
            align=["l", "r"],
        )
    )
    out.append("")
    out.append(f"TOTAL ON HAND  {format_int(report.total_on_hand)}")
    out.append(f"MOVEMENTS      {format_int(report.movement_count)}")
    flagged = report.flagged("NEGATIVE")
    if flagged:
        out.append(f"WARNING: {len(flagged)} line(s) with negative stock")
    return "\n".join(out) + "\n"


def render(fmt: str, report: StockReport, ingest: Optional[IngestResult] = None,
           files: Optional[list[IngestResult]] = None) -> str:
    if fmt == "json":
        return render_json(report, ingest, files) + "\n"
    if fmt == "csv":
        return render_csv(report, ingest, files)
    if fmt == "text":
        return render_text(report, ingest, files)
    raise ValueError(f"unknown format {fmt!r}; expected one of {', '.join(FORMATS)}")
