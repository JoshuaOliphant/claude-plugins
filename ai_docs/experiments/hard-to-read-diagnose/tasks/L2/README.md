# ledgerly

Invoice ledger totals and reports from the billing system's line-level CSV export.
Standard library only (Python 3.11+).

    python -m ledgerly invoice total data/invoices_2025.csv [--by-customer]
    python -m ledgerly invoice list  data/invoices_2025.csv [--customer C006]
    python -m ledgerly invoice show  data/invoices_2025.csv INV25-00007
    python -m ledgerly report summary data/invoices_2025.csv --payments data/payments_2025.json --as-of 2026-01-15
    python -m ledgerly report aging   data/invoices_2025.csv --payments data/payments_2025.json --as-of 2026-01-15
    python -m ledgerly export json|csv data/invoices_2025.csv [--out FILE]

Settings live in `config/ledgerly.toml` (override with `LEDGERLY_CONFIG`).
Customer master data and month-end FX rates are in `data/`; pass `--customers`
or `--fx-rates` to use other files. All totals are reported in the base currency.
