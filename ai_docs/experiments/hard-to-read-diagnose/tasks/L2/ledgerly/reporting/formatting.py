"""Plain-text formatting helpers shared by all commands."""

from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from ..money import Money

RULE_WIDTH = 64


def format_money(money: Money) -> str:
    return f"{money.amount:,.2f} {money.currency}"


def format_number(value: float) -> str:
    return f"{value:,.0f}"


def format_pct(value: Decimal | None, signed: bool = True) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.1f}%" if signed else f"{value:.1f}%"


def format_quantity(value: Decimal) -> str:
    normalized = value.normalize()
    text = format(normalized, "f")
    return text


def truncate(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    return text[: max(0, width - 1)] + "…"


def rule(char: str = "-", width: int = RULE_WIDTH) -> str:
    return char * width


def key_values(pairs: Sequence[tuple[str, str]], label_width: int = 20) -> list[str]:
    return [f"{label + ':':<{label_width}}{value}" for label, value in pairs]


def render_table(
    headers: Sequence[str], rows: Sequence[Sequence[str]], align: str | None = None
) -> list[str]:
    """Render rows as fixed-width columns; ``align`` is a string of l/r per column."""
    align = align or "l" * len(headers)
    widths = [len(h) for h in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def fmt(cells: Sequence[str]) -> str:
        parts = []
        for index, cell in enumerate(cells):
            if align[index] == "r":
                parts.append(cell.rjust(widths[index]))
            else:
                parts.append(cell.ljust(widths[index]))
        return "  ".join(parts).rstrip()

    lines = [fmt(headers), "  ".join("-" * w for w in widths)]
    lines.extend(fmt(row) for row in rows)
    return lines
