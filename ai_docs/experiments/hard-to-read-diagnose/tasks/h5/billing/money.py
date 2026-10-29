def to_cents(amount):
    """Dollar amount from the price feed to whole cents."""
    return int(amount * 100)


def fmt(cents):
    return f"${cents // 100}.{cents % 100:02d}"
