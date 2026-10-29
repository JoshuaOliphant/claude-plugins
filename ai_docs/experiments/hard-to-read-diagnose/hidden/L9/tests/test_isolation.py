"""Requests summarized in one process must not affect each other."""

import json
import os
import subprocess
import sys
from pathlib import Path

TREE = Path(__file__).resolve().parent.parent

GIFT_ORDER = {
    "order_id": "W-9001",
    "customer_id": "C-1001",
    "channel": "web",
    "placed_on": "2026-03-02",
    "lines": [{"sku": "SCARF-MER", "quantity": 1, "gift": True}, {"sku": "TEA-ASSAM", "quantity": 2}],
    "fulfillment": {"gift_note": "Happy birthday, Mum!"},
}

PLAIN_ORDER = {
    "order_id": "W-9002",
    "customer_id": "C-1002",
    "channel": "web",
    "placed_on": "2026-03-02",
    "lines": [{"sku": "MUG-STONE", "quantity": 2}, {"sku": "HONEY-RAW", "quantity": 1}],
}


def _fresh_summary(payload):
    """Summarize a single request in a brand-new interpreter."""
    code = (
        "import json, sys\n"
        "from basketry import api\n"
        "print(json.dumps(api.summarize(json.loads(sys.stdin.read())), sort_keys=True))\n"
    )
    env = dict(os.environ, PYTHONHASHSEED="0", PYTHONDONTWRITEBYTECODE="1")
    env.pop("BASKETRY_SETTINGS", None)
    env.pop("BASKETRY_DATA_DIR", None)
    proc = subprocess.run(
        [sys.executable, "-c", code], input=json.dumps(payload), capture_output=True,
        text=True, cwd=TREE, env=env, timeout=30, check=True,
    )
    return json.loads(proc.stdout)


def test_gift_order_shows_its_own_packed_items(api):
    summary = api.summarize(GIFT_ORDER)
    assert summary["packed_items"] == [
        "Gift wrap: Merino Wool Scarf",
        'Gift message card: "Happy birthday, Mum!"',
    ]


def test_later_customer_does_not_see_earlier_customers_items(api):
    api.summarize(GIFT_ORDER)
    summary = api.summarize(PLAIN_ORDER)
    assert summary["packed_items"] == []
    text = api.summarize_text(PLAIN_ORDER)
    assert "Merino" not in text
    assert "Happy birthday" not in text


def test_summary_independent_of_request_history(api):
    alone = _fresh_summary(PLAIN_ORDER)
    for _ in range(3):
        api.summarize(GIFT_ORDER)
    after = api.summarize(PLAIN_ORDER)
    assert after == alone


def test_repeating_a_request_gives_the_same_summary(api):
    first = api.summarize(GIFT_ORDER)
    second = api.summarize(GIFT_ORDER)
    third = api.summarize(GIFT_ORDER)
    assert first == second == third
    assert first == _fresh_summary(GIFT_ORDER)


def test_free_sample_not_inherited_by_small_pickup_order(api):
    big = {
        "order_id": "S-9001", "customer_id": "C-1005", "channel": "store",
        "lines": [{"sku": "THROW-LIN", "quantity": 1}],
    }
    small = {
        "order_id": "S-9002", "customer_id": "C-1007", "channel": "store",
        "lines": [{"sku": "CARDS-PLAY", "quantity": 1}],
    }
    assert api.summarize(big)["packed_items"] == ["Free sample: Lavender Soap Bar"]
    assert api.summarize(small)["packed_items"] == []


def test_isolation_across_channels_and_customers(api):
    orders = [
        {"order_id": f"A-{i}", "customer_id": cid, "channel": "app",
         "lines": [{"sku": sku, "quantity": 1, "gift": True}]}
        for i, (cid, sku) in enumerate(
            [("C-1003", "CANDLE-CED"), ("C-1004", "PEN-FTN"), ("C-1006", "MUG-STONE")]
        )
    ]
    for order in orders:
        summary = api.summarize(order)
        product = summary["lines"][0]["name"]
        assert summary["packed_items"] == [f"Gift wrap: {product}"], summary["customer_id"]


def test_explicit_inserts_are_kept_and_not_shared(api):
    with_flyer = {
        "order_id": "A-9100", "customer_id": "C-1003", "channel": "app",
        "lines": [{"sku": "JOURNAL-LTH", "quantity": 1, "gift": True}],
        "fulfillment": {"inserts": [{"kind": "flyer", "label": "Spring stationery catalogue"}]},
    }
    assert api.summarize(with_flyer)["packed_items"] == [
        "Spring stationery catalogue",
        "Gift wrap: Leather Journal",
    ]
    other = {"order_id": "A-9101", "customer_id": "C-1008", "channel": "app",
             "lines": [{"sku": "SOCK-HIKE", "quantity": 1}]}
    assert api.summarize(other)["packed_items"] == []


def test_channel_defaults_still_apply(api):
    phone = {"order_id": "P-9200", "customer_id": "C-1002", "channel": "phone",
             "lines": [{"sku": "MUG-STONE", "quantity": 1}]}
    store = {"order_id": "S-9200", "customer_id": "C-1002", "channel": "store",
             "lines": [{"sku": "MUG-STONE", "quantity": 1}]}
    app = {"order_id": "A-9200", "customer_id": "C-1002", "channel": "app",
           "lines": [{"sku": "MUG-STONE", "quantity": 1}]}
    assert api.summarize(phone)["shipping_label"] == "Shipping (express)"
    assert api.summarize(store)["shipping_label"] == "Store pickup"
    assert any("grace@example.org" in n for n in api.summarize(app)["notes"])
    web = dict(phone, order_id="W-9200", channel="web")
    assert api.summarize(web)["shipping_label"] == "Shipping (standard)"
