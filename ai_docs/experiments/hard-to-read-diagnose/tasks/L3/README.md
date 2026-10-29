# stockflow

Ingests stock movement exports (receipts, shipments, adjustments, transfers,
returns) from the warehouse management systems and produces an on-hand report
per warehouse and SKU, starting from the balances of the last stock count.

    python -m stockflow catalog
    python -m stockflow validate data/movements/*.csv
    python -m stockflow import data/movements/*.csv            # one file after another
    python -m stockflow batch data/movements --workers 8       # files in parallel
    python -m stockflow batch data/movements --format json -o report.json

Reference data lives in `data/` and is configured in `stockflow.ini`
(override with `--config` or `STOCKFLOW_CONFIG`). Quantities are converted to
each SKU's base unit; cases use the SKU's own case size where one is defined.
Re-exported lines (same warehouse, reference and SKU) are posted only once.
