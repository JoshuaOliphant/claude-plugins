import csv
import io
import itertools

from .source import fetch_rows


def normalise(rows):
    for r in rows:
        yield {**r, "name": r["name"].upper()}


def preview_lines(rows, n=3):
    return [f"{r['id']}: {r['name']}" for r in itertools.islice(rows, n)]


def export_csv(preview=False, n=120):
    rows = normalise(fetch_rows(n))
    shown = preview_lines(rows) if preview else []
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=["id", "name", "qty"])
    w.writeheader()
    w.writerows(rows)
    return {"csv": out.getvalue(), "preview": shown}
