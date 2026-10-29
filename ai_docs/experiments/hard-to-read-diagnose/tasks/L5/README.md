# stockroom

Inventory and order desk for a small office-furniture distributor with two
warehouses (`MAIN`, `EAST`). Pure Python 3 standard library; data lives in
the SQLite file `data/stockroom.db`.

## Usage

```
python -m stockroom products
python -m stockroom stock LMP-220
python -m stockroom receive LMP-220 12 --warehouse MAIN --unit-cost 23.10 --ref PO-7802
python -m stockroom import-receipts data/receipts_sample.csv
python -m stockroom count CHR-310 13 --warehouse MAIN
python -m stockroom transfer PAD-700 12 --from MAIN --to EAST
python -m stockroom order place --customer C003 --line CHR-310:2 --line MON-410:2
python -m stockroom order ship SO-1043
python -m stockroom order cancel SO-1043
python -m stockroom report availability [--sku SKU] [--warehouse W] [--format json]
python -m stockroom report valuation | reorder | open-orders | moves
```

Point at another database with `--db PATH` or `STOCKROOM_DB=PATH`. Pin the
business date with `STOCKROOM_TODAY=YYYY-MM-DD`.

## Concepts

* **On hand** – units physically in a warehouse.
* **Reserved** – units promised to open order lines at that warehouse.
  Customers with backorders enabled may reserve more than is on hand.
* **Available** – on hand minus reserved, never below zero. Customers
  without backorders can only order from available stock, and only
  available stock can be transferred.
* **Backordered** – reserved units not yet covered by stock on hand.

Schema changes go in `stockroom/db/migrations.py`; they run automatically
the first time the tool opens a database.
