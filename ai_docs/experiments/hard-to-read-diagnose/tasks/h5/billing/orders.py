import json
from pathlib import Path

from .money import to_cents

FEED = Path(__file__).resolve().parent.parent / "data" / "feed.json"
TAX_PERCENT = 8


def load_feed(path=FEED):
    return json.loads(Path(path).read_text())


def order_total(order_id, feed=None):
    feed = feed or load_feed()
    order = feed["orders"][order_id]
    subtotal = sum(to_cents(feed["prices"][sku]) * qty for sku, qty in order.items())
    tax = round(subtotal * TAX_PERCENT / 100)
    return subtotal + tax
