"""Feed readers.

Every reader yields ``(line_no, row)`` pairs where *row* maps the
supplier's own column names to raw string values.  Column mapping onto
catalog fields happens later in the pipeline.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Iterator

from stockline.domain.errors import FeedFormatError

_SNIFF_BYTES = 4096


def detect_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in (".csv", ".txt"):
        return "csv"
    if suffix in (".jsonl", ".ndjson"):
        return "jsonl"
    if suffix == ".tsv":
        return "tsv"
    raise FeedFormatError(str(path), f"unsupported feed extension {suffix!r}")


def read_csv(stream: io.TextIOBase, source: str, delimiter: str | None = None) -> Iterator[tuple[int, dict]]:
    head = stream.read(_SNIFF_BYTES)
    stream.seek(0)
    if delimiter is None:
        try:
            delimiter = csv.Sniffer().sniff(head, delimiters=",;|\t").delimiter
        except csv.Error:
            delimiter = ","
    reader = csv.DictReader(stream, delimiter=delimiter)
    if not reader.fieldnames:
        raise FeedFormatError(source, "missing header row")
    header = [h.strip() for h in reader.fieldnames]
    if len(set(header)) != len(header):
        raise FeedFormatError(source, "duplicate column names in header")
    reader.fieldnames = header
    for row in reader:
        if None in row:
            raise FeedFormatError(source, f"line {reader.line_num}: too many fields")
        if not any((v or "").strip() for v in row.values()):
            continue
        yield reader.line_num, {k: (v or "").strip() for k, v in row.items()}


def read_jsonl(stream: io.TextIOBase, source: str) -> Iterator[tuple[int, dict]]:
    for line_no, line in enumerate(stream, start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise FeedFormatError(source, f"line {line_no}: {exc.msg}") from exc
        if not isinstance(obj, dict):
            raise FeedFormatError(source, f"line {line_no}: expected an object")
        yield line_no, {str(k): "" if v is None else v for k, v in obj.items()}


def open_feed(path: str | Path, fmt: str | None = None) -> Iterator[tuple[int, dict]]:
    path = Path(path)
    if not path.exists():
        raise FeedFormatError(str(path), "file not found")
    fmt = fmt or detect_format(path)
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        if fmt == "csv":
            yield from read_csv(fh, str(path))
        elif fmt == "tsv":
            yield from read_csv(fh, str(path), delimiter="\t")
        elif fmt == "jsonl":
            yield from read_jsonl(fh, str(path))
        else:
            raise FeedFormatError(str(path), f"unknown format {fmt!r}")
