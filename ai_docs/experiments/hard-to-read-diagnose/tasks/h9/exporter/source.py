def fetch_rows(n=120):
    """Rows come from a paged API; they can only be walked once."""
    for i in range(n):
        yield {"id": i + 1, "name": f"item-{i + 1}", "qty": (i * 7) % 13}
