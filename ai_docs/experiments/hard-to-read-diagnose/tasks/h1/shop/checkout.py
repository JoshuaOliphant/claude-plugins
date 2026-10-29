from .promotions import build_lines, bulk_discount, category_discount

TAX_RATE = {"produce": 0, "bakery": 0, "dairy": 0, "default": 8}


def line_total(line):
    unit = line["item"].price_cents - line["unit_off"]
    subtotal = unit * line["qty"]
    rate = TAX_RATE.get(line["item"].category, TAX_RATE["default"])
    return subtotal + round(subtotal * rate / 100)


def total(order, dairy_sale=False):
    lines = build_lines(order)
    if dairy_sale:
        lines = category_discount(lines, "dairy", 10)
    lines = bulk_discount(lines, threshold_qty=6, cents_off=10)
    return sum(line_total(l) for l in lines)
