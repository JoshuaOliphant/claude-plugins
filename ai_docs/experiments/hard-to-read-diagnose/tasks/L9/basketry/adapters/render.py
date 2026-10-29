"""Renderers that turn an :class:`OrderSummary` into text for customers."""

from __future__ import annotations

import json

from ..domain.summary import OrderSummary
from ..utils.registry import register_renderer
from ..utils.text import bullet_list, money, rule, two_column
from .codec import encode_summary


@register_renderer("text")
def render_text(summary: OrderSummary) -> str:
    cur = summary.currency
    out: list[str] = []
    out.append(f"Order {summary.order_id} for {summary.customer_name} ({summary.customer_id})")
    meta = f"Channel: {summary.channel}"
    if summary.placed_on:
        meta += f"   Placed: {summary.placed_on}"
    out.append(meta)
    out.append(rule())
    for line in summary.lines:
        label = f"{line.quantity} x {line.name}"
        if line.gift:
            label += " [gift]"
        out.append(two_column(label, money(line.total_cents, cur)))
    out.append(rule())
    out.append(two_column("Subtotal", money(summary.subtotal_cents, cur)))
    for adj in summary.adjustments:
        out.append(two_column(f"  {adj.description}", money(adj.amount_cents, cur)))
    out.append(two_column(summary.shipping_label or "Shipping", money(summary.shipping_cents, cur)))
    out.append(two_column("Tax", money(summary.tax_cents, cur)))
    out.append(two_column("Total", money(summary.total_cents, cur)))
    if summary.packed_items:
        out.append("")
        out.append("Packed with your order:")
        out.extend(bullet_list(summary.packed_items))
    if summary.boxes:
        out.append("")
        out.append(f"Ships in {summary.boxes} box{'es' if summary.boxes != 1 else ''}.")
    for note in summary.notes:
        out.append(f"Note: {note}")
    return "\n".join(out)


@register_renderer("json")
def render_json(summary: OrderSummary) -> str:
    return json.dumps(encode_summary(summary), sort_keys=True)
