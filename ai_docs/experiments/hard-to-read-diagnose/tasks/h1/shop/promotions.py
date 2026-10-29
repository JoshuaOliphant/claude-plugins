from .catalog import lookup


def category_discount(lines, category, percent):
    """Apply percent off to every line in a category."""
    for line in lines:
        if line["item"].category == category:
            line["item"].price_cents = round(line["item"].price_cents * (100 - percent) / 100)
    return lines


def bulk_discount(lines, threshold_qty, cents_off):
    for line in lines:
        if line["qty"] >= threshold_qty:
            line["unit_off"] = cents_off
    return lines


def build_lines(order):
    return [{"item": lookup(sku), "qty": qty, "unit_off": 0} for sku, qty in order.items()]
