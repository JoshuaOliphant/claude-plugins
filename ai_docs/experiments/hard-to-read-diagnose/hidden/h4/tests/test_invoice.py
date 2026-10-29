from invoicer.invoice import build_invoice


def test_plain_order():
    assert build_invoice(1040)["total_cents"] == 6 * 120 + 450


def test_order_with_cheese():
    inv = build_invoice(1042)
    assert inv["pending"] == []
    assert inv["total_cents"] == 1299 + 389 + 2 * 650


def test_other_orders_unchanged():
    assert build_invoice(1041)["total_cents"] == 2 * 389 + 420
    assert build_invoice(1043)["total_cents"] == 899 + 3 * 575
