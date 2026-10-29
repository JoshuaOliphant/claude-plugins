import json
from pathlib import Path

from billing.orders import load_feed, order_total

EXPECTED = json.loads((Path(__file__).parent / "expected.json").read_text())


def test_every_order_matches_accounting():
    feed = load_feed()
    wrong = {k: (order_total(k, feed), v) for k, v in EXPECTED.items() if order_total(k, feed) != v}
    assert wrong == {}
