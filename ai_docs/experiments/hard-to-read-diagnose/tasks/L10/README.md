# ledgerflow

Imports bank statements (CSV), card processor exports (JSON lines) and partner
card feeds into a single JSON-lines ledger, converting every amount into the
ledger's base currency and categorising it from `data/categories.json`.

```
python -m ledgerflow import config/partner.toml            # nightly partner feed import
python -m ledgerflow import config/all.toml --no-validate  # month-end consolidation
python -m ledgerflow check config/all.toml                 # sample sources, report problems
python -m ledgerflow report out/partner-ledger.jsonl
python -m ledgerflow feeds config/all.toml
```

Layout:

- `ledgerflow/sources/` – one reader per source kind (`csv`, `jsonl`, `feed`)
- `ledgerflow/feeds/` – partner feed transport and paginating client
- `ledgerflow/pipeline.py` – read, validate, normalise, stage and commit each source
- `ledgerflow/validation.py` – optional strict mode (`--validate` or `[validation] enabled`)
- `feeds/` – recorded partner feed snapshots served by the directory transport
- `samples/` – example bank and card exports
- `data/` – FX rates and categorisation rules

Each source is staged in full before it is committed, and transient feed errors
(gateway timeouts, throttling) are retried according to `[retry]`. A source
that still fails after the last attempt aborts the run without writing a ledger.

The importer can also be driven from Python:

```python
from ledgerflow import run_import
result = run_import("config/partner.toml", validate=True)
print(result.imported)
```
