# tillbook

Point-of-sale ledger and reporting for the retail offices (Mumbai, Los Angeles,
London, Singapore). Python 3.11+, standard library only.

```
python -m tillbook offices
python -m tillbook daily-totals --office BOM --date 2026-03-14 [--to 2026-03-15] [--json]
python -m tillbook weekly --office LAX --date 2026-03-14
python -m tillbook top-items --office BOM --from 2026-03-12 --to 2026-03-14
python -m tillbook consolidated --date 2026-03-14
python -m tillbook validate
python -m tillbook close-status --date 2026-03-14
```

Days are always the office's own calendar day (Mumbai reports run midnight to
midnight IST). Data lives in `data/`: till exports in `data/transactions/*.jsonl`,
the payment provider's refund settlements in `data/refunds.csv`, office
registry in `data/offices.json` and treasury FX rates in `data/fx_rates.csv`.
Settings are in `config/settings.ini`; any key can be overridden with a
`TILLBOOK_<KEY>` environment variable.
