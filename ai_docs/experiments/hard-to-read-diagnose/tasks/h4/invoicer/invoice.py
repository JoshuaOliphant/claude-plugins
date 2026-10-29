import json
import logging

from .prices import DATA, load_prices

log = logging.getLogger(__name__)


def build_invoice(order_id, orders_path=DATA / "orders.json", prices_path=DATA / "prices.csv"):
    order = json.loads(open(orders_path).read())[str(order_id)]
    prices = load_prices(prices_path)
    lines, pending = [], []
    for sku, qty in order.items():
        unit = prices.get(sku.strip())
        if unit is None:
            log.warning("no price for %s, left for manual pricing", sku)
            pending.append(sku)
            continue
        lines.append({"sku": sku, "qty": qty, "cents": unit * qty})
    return {
        "order": str(order_id),
        "lines": lines,
        "pending": pending,
        "total_cents": sum(l["cents"] for l in lines),
    }
