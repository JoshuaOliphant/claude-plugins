import csv
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def load_prices(path=DATA / "prices.csv"):
    with open(path, newline="", encoding="utf-8") as f:
        return {row["sku"].strip(): int(row["price_cents"]) for row in csv.DictReader(f)}
