SALES = [
    {"region": "west", "amount": 120.555, "refund": False},
    {"region": "west", "amount": 80.125, "refund": False},
    {"region": "west", "amount": 15.0, "refund": True},
    {"region": "east", "amount": 99.999, "refund": False},
    {"region": "east", "amount": 10.004, "refund": True},
]


def rows_for(region):
    return [r for r in SALES if r["region"] == region]
