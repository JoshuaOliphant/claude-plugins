from dataclasses import dataclass


@dataclass
class Item:
    sku: str
    price_cents: int
    category: str


DEFAULT_CATALOG = {
    "APL": Item("APL", 120, "produce"),
    "BRD": Item("BRD", 450, "bakery"),
    "MLK": Item("MLK", 389, "dairy"),
    "CHS": Item("CHS", 1299, "dairy"),
}


def lookup(sku, catalog=DEFAULT_CATALOG):
    return catalog[sku]
