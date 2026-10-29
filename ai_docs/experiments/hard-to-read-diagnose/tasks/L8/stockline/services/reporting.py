"""Plain-text rendering for the CLI and the nightly e-mail."""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from decimal import Decimal
from typing import Iterable

from stockline.domain.categories import CategoryTree
from stockline.domain.models import Change, ImportRun, Product
from stockline.domain.money import format_money
from stockline.domain.units import each_cost
from stockline.utils.text import truncate

EXPORT_COLUMNS = ("sku", "name", "supplier_code", "supplier_part", "category",
                  "uom", "pack_size", "cost", "price", "status")


def render_report(report, currency: str = "USD", max_rejects: int = 20) -> str:
    run = report.run
    lines = [
        f"Import {run.run_id} ({run.source}) — {run.status}",
        f"  rows seen   {run.rows_seen:>8}",
        f"  created     {run.created:>8}",
        f"  updated     {run.updated:>8}",
        f"  unchanged   {run.unchanged:>8}",
        f"  duplicates  {run.duplicates:>8}",
        f"  rejected    {run.rejected:>8}",
    ]
    if run.discontinued:
        lines.append(f"  discontinued{run.discontinued:>8}")
    if report.match_stats:
        stats = ", ".join(f"{k}={v}" for k, v in sorted(report.match_stats.items()))
        lines.append(f"  matched by  {stats}")
    if report.rejects:
        lines.append("Rejected rows:")
        for rej in report.rejects[:max_rejects]:
            lines.append(f"  line {rej.line_no:>6}  {rej.sku or '-':<16} {'; '.join(rej.reasons)}")
        hidden = len(report.rejects) - max_rejects
        if hidden > 0:
            lines.append(f"  ... and {hidden} more")
    return "\n".join(lines)


def render_product(product: Product, categories: CategoryTree, currency: str = "USD") -> str:
    category = categories.label(product.category) if product.category in categories else product.category
    per_each = each_cost(product.cost, product.uom, product.pack_size)
    return "\n".join([
        f"{product.sku}  {product.name}",
        f"  id          {product.product_id}",
        f"  supplier    {product.supplier_code} part {product.supplier_part or '-'}",
        f"  category    {category}",
        f"  unit        {product.uom} x {product.pack_size}",
        f"  cost        {format_money(product.cost, currency)} ({per_each} each)",
        f"  price       {format_money(product.price, currency)} (margin {product.margin:.1%})",
        f"  status      {product.status}",
        f"  updated     {product.updated_at}",
    ])


def render_history(changes: Iterable[Change]) -> str:
    out = []
    for change in changes:
        detail = ", ".join(
            f"{name}: {before or '∅'} → {after}"
            for name, (before, after) in change.fields.items()
        )
        out.append(f"{change.at}  {change.kind:<12} {change.run_id:<24} {detail}")
    return "\n".join(out) if out else "no changes recorded"


def render_runs(runs: Iterable[ImportRun]) -> str:
    rows = [f"{'run':<26} {'status':<8} {'seen':>7} {'new':>6} {'upd':>6} {'rej':>5}  source"]
    for run in runs:
        rows.append(
            f"{run.run_id:<26} {run.status:<8} {run.rows_seen:>7} {run.created:>6} "
            f"{run.updated:>6} {run.rejected:>5}  {truncate(run.source, 40)}"
        )
    return "\n".join(rows)


def supplier_summary(products: Iterable[Product]) -> list[dict]:
    groups: dict[str, list[Product]] = defaultdict(list)
    for p in products:
        groups[p.supplier_code].append(p)
    summary = []
    for code in sorted(groups):
        items = sorted(groups[code], key=lambda p: p.margin)
        active = [p for p in items if p.status == "active"]
        total_cost = sum((p.cost for p in active), Decimal("0"))
        summary.append({
            "supplier": code,
            "products": len(items),
            "active": len(active),
            "lowest_margin_sku": items[0].sku if items else "",
            "lowest_margin": items[0].margin if items else Decimal("0"),
            "active_cost": total_cost,
        })
    return summary


def render_summary(summary: list[dict], currency: str = "USD") -> str:
    lines = [f"{'supplier':<8} {'products':>8} {'active':>7}  {'lowest margin':<24} active cost"]
    for row in summary:
        low = f"{row['lowest_margin_sku']} ({row['lowest_margin']:.1%})"
        lines.append(
            f"{row['supplier']:<8} {row['products']:>8} {row['active']:>7}  {low:<24} "
            f"{format_money(row['active_cost'], currency)}"
        )
    return "\n".join(lines)


def export_csv(products: Iterable[Product]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(EXPORT_COLUMNS)
    for p in products:
        rec = p.to_record()
        writer.writerow([rec[c] for c in EXPORT_COLUMNS])
    return buf.getvalue()
