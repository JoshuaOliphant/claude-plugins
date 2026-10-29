"""Text helpers used by the human-readable exporters and the CLI."""

from __future__ import annotations

import html
import re
import unicodedata

_WS_RE = re.compile(r"\s+")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def normalize_whitespace(text: str) -> str:
    return _WS_RE.sub(" ", text or "").strip()


def slugify(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return _SLUG_RE.sub("-", folded.lower()).strip("-")


def truncate(text: str, width: int, ellipsis: str = "…") -> str:
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width <= len(ellipsis):
        return text[:width]
    return text[: width - len(ellipsis)] + ellipsis


def pad(text: str, width: int, align: str = "left") -> str:
    if align == "right":
        return text.rjust(width)
    if align == "center":
        return text.center(width)
    return text.ljust(width)


def escape_html(text: str) -> str:
    return html.escape(text or "", quote=True)


def escape_markdown_cell(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def render_table(headers: list[str], rows: list[list[str]], aligns: list[str] | None = None) -> str:
    """Render a plain-text table with column widths fitted to the content."""
    aligns = aligns or ["left"] * len(headers)
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    lines = ["  ".join(pad(h, widths[i], aligns[i]) for i, h in enumerate(headers)).rstrip()]
    lines.append("  ".join("-" * w for w in widths))
    for row in rows:
        lines.append("  ".join(pad(c, widths[i], aligns[i]) for i, c in enumerate(row)).rstrip())
    return "\n".join(lines)
