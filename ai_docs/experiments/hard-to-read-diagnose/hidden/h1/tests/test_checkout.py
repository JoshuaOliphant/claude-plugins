from shop.checkout import total


def test_plain_order():
    assert total({"APL": 6, "BRD": 1}) == 6 * 110 + 450


def test_dairy_sale():
    assert total({"MLK": 2}, dairy_sale=True) == 2 * 350


def test_regular_price_after_sale_day():
    # A sale-day order followed by a normal order: the normal one pays full price.
    total({"CHS": 1}, dairy_sale=True)
    assert total({"CHS": 1, "MLK": 1}) == 1299 + 389
