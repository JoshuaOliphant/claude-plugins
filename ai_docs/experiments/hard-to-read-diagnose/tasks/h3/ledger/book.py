import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from .resolve import handler_for

DATA = Path(__file__).resolve().parent.parent / "data" / "events.json"


def load(path=DATA):
    doc = json.loads(Path(path).read_text())
    return doc["rates"], doc["events"]


def balances(path=DATA):
    rates, events = load(path)
    out = defaultdict(Decimal)
    for ev in events:
        out[ev["account"]] += handler_for(ev).apply(ev, rates)
    return dict(out)
